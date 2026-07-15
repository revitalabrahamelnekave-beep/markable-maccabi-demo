"""Load and validate config.yaml."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

# Repo root = parent of the peri_agent package directory.
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config.yaml"


class Config:
    """Thin typed wrapper around the parsed config.yaml dict."""

    def __init__(self, data: dict):
        self._d = data

    @classmethod
    def load(cls, path: str | os.PathLike | None = None) -> "Config":
        cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
        if not cfg_path.exists():
            raise FileNotFoundError(f"config.yaml not found at {cfg_path}")
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(data)

    # --- convenience accessors -------------------------------------------
    @property
    def product(self) -> dict:
        return self._d.get("product", {})

    @property
    def llm(self) -> dict:
        return self._d.get("llm", {})

    @property
    def model(self) -> str:
        return self.llm.get("model", "claude-opus-4-8")

    @property
    def effort(self) -> str:
        return self.llm.get("effort", "medium")

    @property
    def max_web_searches(self) -> int:
        return int(self.llm.get("max_web_searches", 3))

    @property
    def geo_queries(self) -> list[str]:
        return list(self._d.get("geo_queries", []))

    @property
    def competitors(self) -> list[dict]:
        return list(self._d.get("competitors", []))

    @property
    def pages_to_audit(self) -> list[str]:
        return list(self._d.get("pages_to_audit", []))

    @property
    def keywords_enabled(self) -> bool:
        return bool(self._d.get("keywords", {}).get("enabled", True))

    @property
    def directories_enabled(self) -> bool:
        return bool(self._d.get("directories", {}).get("enabled", True))

    @property
    def output_dir(self) -> Path:
        return ROOT / self._d.get("output", {}).get("dir", "reports")
