"""config.yaml과 queries.yaml 로딩."""
from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | Path | None = None) -> dict:
    path = Path(path) if path else REPO_ROOT / "config.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def load_queries(path: str | Path | None = None) -> dict:
    path = Path(path) if path else REPO_ROOT / "queries.yaml"
    with open(path) as f:
        return yaml.safe_load(f)
