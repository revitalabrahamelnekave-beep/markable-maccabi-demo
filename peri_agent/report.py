"""Assemble a Markdown report from task results."""

from __future__ import annotations

from datetime import datetime, timezone


def _priority_emoji(p: str) -> str:
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p, "•")


def build(cfg, results: dict, usage_summary: str) -> str:
    p = cfg.product
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out: list[str] = []
    A = out.append

    A(f"# דוח קידום SEO / GEO — {p.get('name')} ({p.get('brand')})")
    A(f"\n**נוצר:** {now}  \n**אתר:** {p.get('url')}")
    A("\n> הסוכן מבצע ניתוח וקריאה בלבד. הוא אינו מגיש טפסים ואינו מפרסם — כל פלט הוא טיוטה לבדיקה ולפעולה אנושית.\n")
    A("\n---\n")

    # ---- Task 1: GEO citation audit ----
    geo = results.get("geo")
    if geo:
        A("## 1. אודיט ציטוטים ב-AI (GEO) — הכי משמעותי\n")
        A(f"**האם Markable מצוטט ע\"י AI:** {geo['cited_count']} מתוך {geo['total']} שאלות "
          f"(**{geo['cited_pct']}%**)\n")
        A("\n| שאלה | Markable מצוטט? | מתחרים שהופיעו | מותגים אחרים |")
        A("|---|:---:|---|---|")
        for r in geo["results"]:
            mark = "✅" if r["brand_cited"] else "❌"
            comps = ", ".join(r["competitors_cited"]) or "—"
            others = ", ".join(r["other_brands"][:5]) or "—"
            q = r["query"].replace("|", "/")
            A(f"| {q} | {mark} | {comps} | {others} |")
        A("\n**איך לפעול:** בכל שאלה שבה ❌ — זו הזדמנות. צור/שפר עמוד תוכן שעונה ישירות "
          "על השאלה (TL;DR ב-200 המילים הראשונות, מבנה שאלה-תשובה, מקורות). Perplexity "
          "מצטט הכי מהר (4–12 שבועות).\n")
        A("\n---\n")

    # ---- Task 2: Page audit ----
    pg = results.get("pages")
    if pg:
        A("## 2. אודיט GEO/SEO של עמודים\n")
        for a in pg["audits"]:
            A(f"### {a.get('url')}")
            if a.get("error"):
                A(f"\n⚠️ לא ניתן היה להוריד את העמוד: `{a['error']}`\n")
                A("(ייתכן חסימת בוט / Cloudflare. הרץ מהמחשב שלך, או בדוק ידנית.)\n")
                continue
            A(f"\n**ציון מוכנות ל-AI:** {a.get('geo_readiness_score', '?')}/100\n")
            if a.get("strengths"):
                A("\n**חוזקות:**")
                for s in a["strengths"]:
                    A(f"- {s}")
            recs = a.get("recommendations", [])
            if recs:
                A("\n\n**המלצות (לפי עדיפות):**\n")
                A("| עדיפות | תחום | בעיה | תיקון |")
                A("|:---:|---|---|---|")
                order = {"high": 0, "medium": 1, "low": 2}
                for r in sorted(recs, key=lambda x: order.get(x.get("priority"), 3)):
                    A(f"| {_priority_emoji(r['priority'])} {r['priority']} | {r['area']} "
                      f"| {r['issue']} | {r['fix']} |")
            f = a.get("facts", {})
            if f:
                A(f"\n<details><summary>עובדות שנאספו מהעמוד</summary>\n\n"
                  f"- Title ({f.get('title_len')} תווים): {f.get('title') or '—'}\n"
                  f"- Meta description ({f.get('meta_len')} תווים): {f.get('meta_description') or '—'}\n"
                  f"- מספר מילים: {f.get('word_count')}\n"
                  f"- schema.org: {', '.join(f.get('schema_types', [])) or '❌ אין'}\n"
                  f"- FAQ schema: {'✅' if f.get('has_faq_schema') else '❌'}\n"
                  f"- טבלאות: {f.get('tables_count')}\n"
                  f"- תמונות עם alt: {f.get('images_with_alt')}/{f.get('images_total')}\n"
                  f"</details>\n")
            A("")
        A("\n---\n")

    # ---- Task 3: Keywords ----
    kw = results.get("keywords")
    if kw and kw.get("keywords"):
        A("## 3. מילות מפתח ורעיונות תוכן\n")
        A("| שאילתה | שפה | כוונה | רעיון תוכן | הערת GEO |")
        A("|---|:---:|---|---|---|")
        for k in kw["keywords"]:
            A(f"| {k.get('query')} | {k.get('lang')} | {k.get('intent')} "
              f"| {k.get('content_idea')} | {k.get('geo_note')} |")
        A("\n---\n")

    # ---- Task 4: Directories ----
    d = results.get("directories")
    if d:
        A("## 4. ערכת הגשה לדיירקטוריז (להדבקה ידנית)\n")
        A("> ⚠️ הגש רק לדיירקטוריז איכותיים. ספאם המוני מזיק ל-SEO. הרשימה מסוננת לאיכות.\n")
        c = d.get("copy", {})
        if c:
            A("\n### טקסטים מוכנים\n")
            A(f"- **Tagline (עברית):** {c.get('tagline_he','')}")
            A(f"- **Tagline (English):** {c.get('tagline_en','')}")
            A(f"- **תיאור קצר (עברית):** {c.get('short_desc_he','')}")
            A(f"- **Short description (English):** {c.get('short_desc_en','')}")
            A(f"- **Long description (English):** {c.get('long_desc_en','')}")
            A(f"- **קטגוריות מוצעות:** {', '.join(c.get('suggested_categories', []))}")
        dirs = d.get("directories", [])
        if dirs:
            A("\n### דיירקטוריז מומלצים\n")
            A("| עדיפות | שם | קישור | עלות | למה |")
            A("|:---:|---|---|:---:|---|")
            order = {"high": 0, "medium": 1, "low": 2}
            for x in sorted(dirs, key=lambda i: order.get(i.get("priority"), 3)):
                A(f"| {_priority_emoji(x['priority'])} | {x['name']} | {x['url']} "
                  f"| {x['cost']} | {x['why']} |")
        A("\n---\n")

    A(f"\n_עלות ריצה משוערת: {usage_summary}_\n")
    return "\n".join(out)
