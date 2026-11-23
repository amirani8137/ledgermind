"""Load config.toml. Relative paths are resolved against the config file's folder."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Source:
    pattern: str
    importer: str
    account: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    ledger: Path
    inbox: Path
    imports_dir: Path
    rules: Path | None
    review_threshold: float
    sources: list[Source]
    llm: dict[str, Any]


def load_config(path: str | Path) -> Config:
    path = Path(path).resolve()
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    base = path.parent

    def p(key: str, default: str | None = None) -> Path | None:
        value = raw.get(key, default)
        return (base / value).resolve() if value else None

    try:
        sources = [Source(**s) for s in raw.get("sources", [])]
        ledger = p("ledger")
        inbox = p("inbox")
    except TypeError as e:
        raise ValueError(f"{path}: invalid [[sources]] entry: {e}") from None
    if ledger is None or inbox is None:
        raise ValueError(f"{path}: 'ledger' and 'inbox' are required")

    return Config(
        ledger=ledger,
        inbox=inbox,
        imports_dir=p("imports_dir") or ledger.parent / "imports",
        rules=p("rules"),
        review_threshold=float(raw.get("review_threshold", 0.8)),
        sources=sources,
        llm=raw.get("llm", {}),
    )
