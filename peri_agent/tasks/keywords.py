"""Task 3 — Keyword & content-gap ideation (no web-search cost).

Generates high-intent Hebrew + English queries the audience asks, maps each to
a content idea (comparison page, FAQ, guide), and flags gaps. Pure model call.
"""

from __future__ import annotations

import json

from ..config import Config
from ..llm import LLM

_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "lang": {"type": "string", "enum": ["he", "en"]},
                    "intent": {"type": "string", "enum": ["informational", "commercial", "navigational"]},
                    "content_idea": {"type": "string"},
                    "geo_note": {"type": "string", "description": "How to structure it for AI citation"},
                },
                "required": ["query", "lang", "intent", "content_idea", "geo_note"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["keywords"],
    "additionalProperties": False,
}


def run(cfg: Config, llm: LLM) -> dict:
    p = cfg.product
    prompt = (
        f"Product: {p.get('name')} — {p.get('one_liner_en')}\n"
        f"Audience: Hebrew-speaking women approaching or in perimenopause.\n\n"
        "Produce 12-15 high-intent search queries this audience actually types "
        "(mix Hebrew and English). For each: intent, a specific content idea "
        "(comparison page, FAQ, guide, checklist), and a one-line GEO note on how "
        "to structure the content so ChatGPT/Perplexity/Google AI cite it. Favor "
        "queries where a small femtech tool can realistically win — long-tail, "
        "question-shaped, and comparison intents."
    )
    data = llm.ask_json(prompt, _SCHEMA, max_tokens=3000)
    return {"keywords": data.get("keywords", []) if isinstance(data, dict) else []}
