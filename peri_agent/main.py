"""PERI-AGENT entry point.

Runs the SEO/GEO tasks and writes a timestamped Markdown report.

Usage:
    python -m peri_agent.main                # run all tasks
    python -m peri_agent.main --only geo     # run one task (geo|pages|keywords|directories)
    python -m peri_agent.main --dry-run      # print plan + cost estimate, call nothing

Credentials: set ANTHROPIC_API_KEY (or run `ant auth login`).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from . import report
from .config import Config
from .llm import LLM
from .tasks import directories, geo_citation, keywords, page_audit

ALL_TASKS = ["geo", "pages", "keywords", "directories"]


def _plan(cfg: Config, tasks: list[str]) -> None:
    print("PERI-AGENT — plan\n")
    print(f"  product : {cfg.product.get('name')} ({cfg.product.get('url')})")
    print(f"  model   : {cfg.model}  (effort={cfg.effort})")
    print(f"  tasks   : {', '.join(tasks)}")
    if "geo" in tasks:
        print(f"  geo     : {len(cfg.geo_queries)} queries × web search "
              f"(≤{cfg.max_web_searches} searches each)")
    if "pages" in tasks:
        print(f"  pages   : {len(cfg.pages_to_audit)} page(s)")
    print("\n  NOTE: read-only. The agent never submits forms or posts content.")
    print("  Web search is the main cost driver — reduce geo_queries to lower cost.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MARKABLE SEO/GEO agent")
    ap.add_argument("--only", choices=ALL_TASKS, help="run a single task")
    ap.add_argument("--dry-run", action="store_true", help="show plan + exit")
    ap.add_argument("--config", default=None, help="path to config.yaml")
    args = ap.parse_args(argv)

    cfg = Config.load(args.config)
    tasks = [args.only] if args.only else ALL_TASKS
    # respect enable flags (a single --only task the user explicitly asked for still runs)
    if not args.only and not cfg.keywords_enabled:
        tasks = [t for t in tasks if t != "keywords"]
    if not args.only and not cfg.directories_enabled:
        tasks = [t for t in tasks if t != "directories"]

    _plan(cfg, tasks)
    if args.dry_run:
        return 0

    llm = LLM(model=cfg.model, effort=cfg.effort)
    results: dict = {}

    try:
        if "geo" in tasks:
            print("\n[1/4] GEO citation audit…", flush=True)
            results["geo"] = geo_citation.run(cfg, llm)
        if "pages" in tasks:
            print("[2/4] Page audit…", flush=True)
            results["pages"] = page_audit.run(cfg, llm)
        if "keywords" in tasks:
            print("[3/4] Keyword ideation…", flush=True)
            results["keywords"] = keywords.run(cfg, llm)
        if "directories" in tasks:
            print("[4/4] Directory kit…", flush=True)
            results["directories"] = directories.run(cfg, llm)
    except Exception as e:  # noqa: BLE001 — surface any failure but still save cost info
        print(f"\n⚠️  Task failed: {e}", file=sys.stderr)

    # Write report
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    md = report.build(cfg, results, llm.usage.summary())
    out_path = cfg.output_dir / f"report-{stamp}.md"
    out_path.write_text(md, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"✅ Report: {out_path}")
    print(f"💰 {llm.usage.summary()}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
