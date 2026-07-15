"""Task 2 — On-page GEO/SEO audit.

Fetch each page (read-only), extract structural facts (title, meta, headings,
schema.org, first 200 words, FAQ/Q&A, tables, images/alt), and ask Claude for
concrete, prioritized recommendations to improve AI-citation readiness.
"""

from __future__ import annotations

import json

import requests
from bs4 import BeautifulSoup

from ..config import Config
from ..llm import LLM

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "geo_readiness_score": {"type": "integer", "description": "0-100"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "area": {"type": "string"},
                    "issue": {"type": "string"},
                    "fix": {"type": "string"},
                },
                "required": ["priority", "area", "issue", "fix"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["geo_readiness_score", "strengths", "recommendations"],
    "additionalProperties": False,
}


def _extract(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        # keep JSON-LD scripts for schema detection
        if tag.name == "script" and tag.get("type") == "application/ld+json":
            continue
        tag.decompose()

    title = (soup.title.string.strip() if soup.title and soup.title.string else "")
    meta_desc = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"].strip()

    headings = [
        f"{h.name}: {h.get_text(strip=True)}"
        for h in soup.find_all(["h1", "h2", "h3"])
    ][:30]

    # schema.org structured data present?
    ld = BeautifulSoup(html, "html.parser").find_all(
        "script", attrs={"type": "application/ld+json"}
    )
    schema_types = []
    for s in ld:
        try:
            data = json.loads(s.string or "{}")
            items = data if isinstance(data, list) else [data]
            for it in items:
                t = it.get("@type")
                if t:
                    schema_types.append(t if isinstance(t, str) else ",".join(t))
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    text = soup.get_text(" ", strip=True)
    first_200 = " ".join(text.split()[:200])

    imgs = soup.find_all("img")
    imgs_with_alt = sum(1 for i in imgs if i.get("alt"))

    return {
        "title": title,
        "title_len": len(title),
        "meta_description": meta_desc,
        "meta_len": len(meta_desc),
        "headings": headings,
        "schema_types": schema_types,
        "has_faq_schema": any("FAQ" in t for t in schema_types),
        "first_200_words": first_200,
        "tables_count": len(soup.find_all("table")),
        "images_total": len(imgs),
        "images_with_alt": imgs_with_alt,
        "word_count": len(text.split()),
    }


def _fetch(url: str) -> tuple[str | None, str | None]:
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=20)
        r.raise_for_status()
        return r.text, None
    except requests.RequestException as e:
        return None, str(e)


def run(cfg: Config, llm: LLM) -> dict:
    audits = []
    for url in cfg.pages_to_audit:
        html, err = _fetch(url)
        if err:
            audits.append({"url": url, "error": err})
            continue

        facts = _extract(html)
        prompt = (
            "You are a GEO (Generative Engine Optimization) + SEO expert auditing a "
            f"femtech health page (product: {cfg.product.get('name')}, audience: Hebrew-"
            "speaking women, perimenopause). Based on the extracted page facts below, "
            "score AI-citation readiness (0-100) and give concrete, prioritized fixes. "
            "Check for: a TL;DR / direct answer in the first 200 words, Q&A/FAQ structure, "
            "schema.org markup (esp. FAQPage), data tables, clear headings, strong title/meta, "
            "image alt text, and E-E-A-T signals (author/date). Recommendations must be "
            "specific and actionable.\n\nPAGE FACTS (JSON):\n" + json.dumps(facts, ensure_ascii=False)
        )
        audit = llm.ask_json(prompt, _AUDIT_SCHEMA, max_tokens=2500)
        audit["url"] = url
        audit["facts"] = facts
        audits.append(audit)
    return {"audits": audits}
