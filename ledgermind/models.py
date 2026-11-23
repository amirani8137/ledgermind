"""Core data model shared by importers, categorizers and the writer.

Importers turn statement rows into `Transaction` objects. A simple bank or card
line only needs `account` + `amount`; a categorizer later fills in
`counter_account`. Complex entries (stock trades, loan splits) can supply
their own `postings` instead, and are then written exactly as given.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

UNCATEGORIZED = "Expenses:Uncategorized"


@dataclass
class Posting:
    """One leg of a Beancount transaction.

    units=None means "auto-balance this leg" (Beancount fills in the amount).
    cost is the per-unit cost for lots ({140.00 USD}); cost_empty=True writes {}
    so Beancount picks the lot to reduce using the account's booking method.
    """

    account: str
    units: Decimal | None = None
    currency: str = "USD"
    cost: Decimal | None = None
    cost_currency: str = "USD"
    cost_empty: bool = False
    price: Decimal | None = None
    price_currency: str = "USD"


@dataclass
class Transaction:
    date: date
    description: str
    amount: Decimal  # signed, from the point of view of `account`
    account: str  # the account the statement belongs to
    payee: str | None = None
    currency: str = "USD"
    source_file: str = ""
    source_line: int = 0
    postings: list[Posting] = field(default_factory=list)
    counter_account: str | None = None
    confidence: float = 0.0
    categorized_by: str = ""
    import_id: str = ""

    def needs_review(self, threshold: float) -> bool:
        if self.postings:
            return self.confidence < threshold
        return self.counter_account in (None, UNCATEGORIZED) or self.confidence < threshold
