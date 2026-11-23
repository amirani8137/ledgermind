"""Categorizer chain.

Each categorizer looks at a transaction and returns (account, confidence) or
None. They are tried in order — cheapest and most predictable first:

  importer (already set) → rules → history → LLM (optional) → Uncategorized

Anything below the review threshold is written with the "!" flag so it shows
up in `ledgermind review` and in Fava.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from ..models import UNCATEGORIZED, Transaction
from .history import HistoryCategorizer
from .llm import LLMCategorizer
from .rules import RulesCategorizer


class Categorizer(Protocol):
    name: str

    def categorize(self, txn: Transaction) -> tuple[str, float] | None: ...


def categorize(txn: Transaction, categorizers: Iterable[Categorizer], valid_accounts: set[str]) -> None:
    """Fill in txn.counter_account in place."""
    if txn.postings or txn.counter_account:
        return  # the importer already decided
    for c in categorizers:
        result = c.categorize(txn)
        if result and result[0] in valid_accounts:
            txn.counter_account, txn.confidence = result
            txn.categorized_by = c.name
            return
    txn.counter_account = UNCATEGORIZED
    txn.confidence = 0.0
    txn.categorized_by = "none"


__all__ = ["Categorizer", "HistoryCategorizer", "LLMCategorizer", "RulesCategorizer", "categorize"]
