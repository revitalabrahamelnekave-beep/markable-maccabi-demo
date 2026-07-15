"""Task 4 — Directory submission kit.

Produces a curated list of HIGH-QUALITY, relevant directories/listings plus
ready-to-paste submission copy (name, taglines, short/long descriptions,
categories) in Hebrew + English.

SAFETY: the agent does NOT submit anything. Low-quality directory spam can
hurt SEO (Google's spam updates target manipulative link patterns), so this
task deliberately curates quality over quantity and leaves submission to a
human who pastes the prepared copy.
"""

from __future__ import annotations

from ..config import Config
from ..llm import LLM

_SCHEMA = {
    "type": "object",
    "properties": {
        "copy": {
            "type": "object",
            "properties": {
                "tagline_he": {"type": "string"},
                "tagline_en": {"type": "string"},
                "short_desc_he": {"type": "string", "description": "~160 chars"},
                "short_desc_en": {"type": "string", "description": "~160 chars"},
                "long_desc_en": {"type": "string", "description": "~400 chars"},
                "suggested_categories": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "tagline_he", "tagline_en", "short_desc_he",
                "short_desc_en", "long_desc_en", "suggested_categories",
            ],
            "additionalProperties": False,
        },
        "directories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"},
                    "why": {"type": "string", "description": "why relevant & quality"},
                    "cost": {"type": "string", "enum": ["free", "freemium", "paid"]},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["name", "url", "why", "cost", "priority"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["copy", "directories"],
    "additionalProperties": False,
}


def run(cfg: Config, llm: LLM) -> dict:
    p = cfg.product
    prompt = (
        f"Product: {p.get('name')} by {p.get('brand')} — {p.get('one_liner_en')}\n"
        f"Site: {p.get('url')}. Categories: {', '.join(p.get('categories', []))}.\n"
        "Audience: Hebrew-speaking women (Israel), perimenopause / femtech / health.\n\n"
        "1) Write ready-to-paste submission copy (Hebrew + English taglines and "
        "descriptions, plus suggested categories). Keep it privacy-forward and "
        "science-backed in tone.\n"
        "2) Recommend 12-18 HIGH-QUALITY, genuinely relevant directories/listings "
        "to submit to — favor femtech/health/startup directories and product-launch "
        "sites with real user bases (e.g. Product Hunt, AlternativeTo, Crunchbase, "
        "BetaList, femtech/health-tech listings). AVOID low-quality link farms — "
        "explain briefly why each one is worth it. Prefer free/freemium. Rank by priority."
    )
    data = llm.ask_json(prompt, _SCHEMA, max_tokens=3500)
    return {
        "copy": data.get("copy", {}) if isinstance(data, dict) else {},
        "directories": data.get("directories", []) if isinstance(data, dict) else [],
    }
