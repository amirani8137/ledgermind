"""Thin wrapper around the Beancount loader."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from beancount import loader
from beancount.core import data

# Always read fresh from disk: the pipeline writes new include files and
# re-validates immediately, so a cached load could be stale.
loader.initialize(use_cache=False)

IN_TRANSIT = "Assets:Transfers:InTransit"


def load(path: Path):
    """Return (entries, errors, options_map)."""
    return loader.load_file(str(path))


def format_error(err) -> str:
    src = getattr(err, "source", None) or {}
    where = f"{src.get('filename', '?')}:{src.get('lineno', '?')}"
    return f"{where}: {err.message}"


def import_ids(entries) -> set[str]:
    return {e.meta["import_id"] for e in entries if isinstance(e, data.Transaction) and "import_id" in e.meta}


def open_accounts(entries) -> set[str]:
    closed = {e.account for e in entries if isinstance(e, data.Close)}
    return {e.account for e in entries if isinstance(e, data.Open)} - closed


def in_transit_balance(entries) -> Decimal:
    """Should be 0 once both sides of every transfer are imported."""
    total = Decimal(0)
    for e in entries:
        if isinstance(e, data.Transaction):
            for p in e.postings:
                if p.account == IN_TRANSIT and p.units is not None:
                    total += p.units.number
    return total


def flagged(entries) -> list:
    return [e for e in entries if isinstance(e, data.Transaction) and e.flag == "!"]
