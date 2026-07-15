"""Claude API wrapper with built-in cost tracking.

Uses the official Anthropic SDK. Credentials resolve from the environment
(ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or an `ant auth login` profile) —
never hardcode a key.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import anthropic

# Pricing per 1M tokens (USD). Source: Anthropic model catalog, 2026.
# Sonnet 5 has an introductory rate through 2026-08-31 ($2/$10); we use the
# standard sticker here so estimates are conservative (never under-report).
PRICING = {
    "claude-opus-4-8": {"in": 5.00, "out": 25.00},
    "claude-opus-4-7": {"in": 5.00, "out": 25.00},
    "claude-sonnet-5": {"in": 3.00, "out": 15.00},
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00},
    "claude-haiku-4-5": {"in": 1.00, "out": 5.00},
    "claude-fable-5": {"in": 10.00, "out": 50.00},
}

# Web search server tool: ~$10 per 1,000 searches (indicative).
WEB_SEARCH_COST_PER_1K = 10.00


@dataclass
class Usage:
    """Accumulates token usage and estimated cost across all calls."""

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    web_searches: int = 0
    calls: int = 0
    _errors: list[str] = field(default_factory=list)

    def add(self, resp) -> None:
        self.calls += 1
        u = resp.usage
        self.input_tokens += getattr(u, "input_tokens", 0) or 0
        self.output_tokens += getattr(u, "output_tokens", 0) or 0
        self.cache_read_tokens += getattr(u, "cache_read_input_tokens", 0) or 0
        # Count web searches from the server_tool_use blocks in the response.
        for block in getattr(resp, "content", []) or []:
            if getattr(block, "type", "") == "server_tool_use" and getattr(block, "name", "") == "web_search":
                self.web_searches += 1

    @property
    def estimated_cost_usd(self) -> float:
        p = PRICING.get(self.model, PRICING["claude-opus-4-8"])
        tok_cost = (self.input_tokens * p["in"] + self.output_tokens * p["out"]) / 1_000_000
        search_cost = self.web_searches * WEB_SEARCH_COST_PER_1K / 1000
        return tok_cost + search_cost

    def summary(self) -> str:
        return (
            f"model={self.model}  calls={self.calls}  "
            f"in={self.input_tokens:,}tok  out={self.output_tokens:,}tok  "
            f"web_searches={self.web_searches}  "
            f"≈ ${self.estimated_cost_usd:.3f}"
        )


class LLM:
    """Small helper around client.messages for the agent's needs."""

    def __init__(self, model: str, effort: str = "medium"):
        self.client = anthropic.Anthropic()
        self.model = model
        self.effort = effort
        self.usage = Usage(model=model)

    def _output_config(self, fmt: dict | None = None) -> dict:
        oc: dict = {"effort": self.effort}
        if fmt:
            oc["format"] = fmt
        return oc

    def ask(self, prompt: str, system: str | None = None, max_tokens: int = 2000) -> str:
        """Plain text completion."""
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system or "",
            output_config=self._output_config(),
            messages=[{"role": "user", "content": prompt}],
        )
        self.usage.add(resp)
        return _text(resp)

    def ask_json(self, prompt: str, schema: dict, system: str | None = None, max_tokens: int = 2000) -> dict:
        """Structured completion validated against a JSON schema."""
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system or "",
            output_config=self._output_config({"type": "json_schema", "schema": schema}),
            messages=[{"role": "user", "content": prompt}],
        )
        self.usage.add(resp)
        try:
            return json.loads(_text(resp))
        except (json.JSONDecodeError, ValueError):
            return {}

    def ask_with_web_search(
        self, prompt: str, system: str | None = None, max_uses: int = 3, max_tokens: int = 3000
    ) -> tuple[str, list[str]]:
        """Answer a question WITH live web search, simulating an AI engine.

        Returns (answer_text, cited_urls).
        """
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system or "",
            output_config=self._output_config(),
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}],
            messages=[{"role": "user", "content": prompt}],
        )
        # Server tools can pause; resume until the turn actually ends.
        messages = [{"role": "user", "content": prompt}]
        guard = 0
        while resp.stop_reason == "pause_turn" and guard < 5:
            guard += 1
            self.usage.add(resp)
            messages.append({"role": "assistant", "content": resp.content})
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or "",
                output_config=self._output_config(),
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}],
                messages=messages,
            )
        self.usage.add(resp)
        return _text(resp), _citations(resp)


def _text(resp) -> str:
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()


def _citations(resp) -> list[str]:
    """Pull every source URL from web_search_tool_result blocks."""
    urls: list[str] = []
    for block in resp.content:
        if getattr(block, "type", "") == "web_search_tool_result":
            content = getattr(block, "content", None)
            # Success content is a list of results; an error content is an object.
            if isinstance(content, list):
                for r in content:
                    url = getattr(r, "url", None)
                    if url:
                        urls.append(url)
    return urls
