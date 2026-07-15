"""Task 1 — GEO citation audit.

For each target question, ask Claude WITH live web search (simulating how an
AI engine like ChatGPT / Perplexity answers), then check whether Markable /
Peritale is cited vs. competitors. This is the highest-value 2026 signal:
being cited by AI engines that already answer 30-40% of queries.
"""

from __future__ import annotations

from ..config import Config
from ..llm import LLM

_BRAND_MARKERS = ["peritale", "markable"]

_MENTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "brands_mentioned": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Names of products/apps/tools named in the answer.",
        },
    },
    "required": ["brands_mentioned"],
    "additionalProperties": False,
}


def run(cfg: Config, llm: LLM) -> dict:
    system = (
        "You are a helpful assistant answering a real user's health question, "
        "the way a search assistant would. Use web search to give a concrete, "
        "practical answer. If specific tools, apps, or services are relevant, "
        "name them."
    )

    competitor_domains = {c.get("url", "").lower(): c.get("name", "") for c in cfg.competitors}
    results = []

    for query in cfg.geo_queries:
        answer, citations = llm.ask_with_web_search(
            query, system=system, max_uses=cfg.max_web_searches
        )
        blob = (answer + " " + " ".join(citations)).lower()

        brand_cited = any(m in blob for m in _BRAND_MARKERS)

        # Which known competitors showed up?
        comps_found = [
            name for dom, name in competitor_domains.items() if dom and dom in blob
        ]

        # Extract any other brands/tools named (structured, cheap, no search).
        extra = {}
        if answer:
            extra = llm.ask_json(
                f"From this answer, list every product/app/tool/service named "
                f"(brand names only, short). Answer:\n\n{answer[:4000]}",
                _MENTIONS_SCHEMA,
                max_tokens=400,
            )
        brands = extra.get("brands_mentioned", []) if isinstance(extra, dict) else []

        results.append(
            {
                "query": query,
                "brand_cited": brand_cited,
                "competitors_cited": comps_found,
                "other_brands": brands,
                "citations": citations[:8],
            }
        )

    cited = sum(1 for r in results if r["brand_cited"])
    return {
        "results": results,
        "total": len(results),
        "cited_count": cited,
        "cited_pct": round(100 * cited / len(results)) if results else 0,
    }
