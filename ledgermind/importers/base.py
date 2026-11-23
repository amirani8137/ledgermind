"""Importer plugin interface and helpers.

To add a new bank or broker:
  1. Create `ledgermind/importers/<name>.py`
  2. Subclass `Importer`, set `name`, implement `extract()`
  3. Decorate the class with `@register`
  4. Import the module in `ledgermind/importers/__init__.py`
  5. Add a fake sample statement + test under `tests/`

See CONTRIBUTING.md for a full walkthrough.
"""

from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ..models import Transaction


class Importer(ABC):
    #: Short identifier used in config.toml (`importer = "chase"`)
    name: str = ""

    @abstractmethod
    def extract(self, path: Path, account: str, options: dict[str, Any]) -> list[Transaction]:
        """Read one statement file and return its transactions.

        `account` is the ledger account the statement belongs to, taken from
        config.toml. `options` holds any importer-specific settings.
        """


_REGISTRY: dict[str, Importer] = {}


def register(cls: type[Importer]) -> type[Importer]:
    if not cls.name:
        raise ValueError(f"{cls.__name__} must define a `name`")
    _REGISTRY[cls.name] = cls()
    return cls


def get_importer(name: str) -> Importer:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"Unknown importer '{name}'. Available: {', '.join(available())}") from None


def available() -> list[str]:
    return sorted(_REGISTRY)


def read_csv_rows(path: Path) -> Iterator[tuple[int, dict[str, str]]]:
    """Yield (line_number, row) with whitespace-stripped keys and values.

    Blank rows are skipped. Extra trailing columns (common in bank exports)
    are ignored.
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {
                k.strip(): (v or "").strip()
                for k, v in row.items()
                if k is not None and not isinstance(v, list)
            }
            if any(clean.values()):
                yield reader.line_num, clean


def parse_amount(text: str | None) -> Decimal:
    """Parse '$1,234.56', '-12.00' or '(12.00)' into a Decimal."""
    if text is None or not text.strip():
        return Decimal(0)
    s = text.strip().replace("$", "").replace(",", "")
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        value = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Cannot parse amount: {text!r}") from None
    return -value if negative else value
