"""Learns from your own ledger.

Every cleared ("*") transaction you have already reviewed teaches it which
account a description belongs to. When you fix an entry in the review queue
and mark it "*", the next statement with the same merchant is categorized
automatically.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from beancount.core import data

from ..models import UNCATEGORIZED, Transaction

CATEGORY_ROOTS = ("Expenses:", "Income:")


def normalize(text: str) -> str:
    """'STARBUCKS STORE 05521 FREMONT' -> 'STARBUCKS STORE FREMONT'."""
    text = re.sub(r"[^A-Z ]+", " ", text.upper())
    return re.sub(r"\s+", " ", text).strip()


class HistoryCategorizer:
    name = "history"

    def __init__(self, entries: list) -> None:
        self.counts: dict[str, Counter[str]] = defaultdict(Counter)
        for e in entries:
            if not isinstance(e, data.Transaction) or e.flag != "*":
                continue
            categories = [
                p.account
                for p in e.postings
                if p.account.startswith(CATEGORY_ROOTS) and p.account != UNCATEGORIZED
            ]
            if len(categories) == 1 and e.narration:
                self.counts[normalize(e.narration)][categories[0]] += 1

    def categorize(self, txn: Transaction) -> tuple[str, float] | None:
        seen = self.counts.get(normalize(txn.description))
        if not seen:
            return None
        account, n = seen.most_common(1)[0]
        confidence = 0.9 if n == sum(seen.values()) else 0.6
        return account, confidence
