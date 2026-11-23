"""Chase checking/savings CSV export.

Expected header:
  Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
Amounts are signed: negative = money out.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import Transaction
from .base import Importer, parse_amount, read_csv_rows, register


@register
class ChaseImporter(Importer):
    name = "chase"

    def extract(self, path: Path, account: str, options: dict[str, Any]) -> list[Transaction]:
        txns = []
        for line, row in read_csv_rows(path):
            txns.append(
                Transaction(
                    date=datetime.strptime(row["Posting Date"], "%m/%d/%Y").date(),
                    description=row["Description"],
                    amount=parse_amount(row["Amount"]),
                    account=account,
                    source_file=path.name,
                    source_line=line,
                )
            )
        return txns
