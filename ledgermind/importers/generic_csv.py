"""Configurable CSV importer for any bank or card with a simple export.

Options (all optional, set under [sources.options] in config.toml):
  date_column         default "Date"
  description_column  default "Description"
  amount_column       default "Amount"   (single signed column), or
  debit_column / credit_column           (two unsigned columns)
  date_format         default "%m/%d/%Y"
  negate              default false. Set true when the export shows charges
                      as positive numbers (most credit cards), so they are
                      recorded as increasing the liability.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import Transaction
from .base import Importer, parse_amount, read_csv_rows, register


@register
class GenericCSVImporter(Importer):
    name = "generic_csv"

    def extract(self, path: Path, account: str, options: dict[str, Any]) -> list[Transaction]:
        date_col = options.get("date_column", "Date")
        desc_col = options.get("description_column", "Description")
        amount_col = options.get("amount_column", "Amount")
        debit_col = options.get("debit_column")
        credit_col = options.get("credit_column")
        date_fmt = options.get("date_format", "%m/%d/%Y")
        negate = bool(options.get("negate", False))

        txns = []
        for line, row in read_csv_rows(path):
            if debit_col or credit_col:
                amount = parse_amount(row.get(credit_col or "", "")) - parse_amount(
                    row.get(debit_col or "", "")
                )
            else:
                amount = parse_amount(row[amount_col])
            if negate:
                amount = -amount
            txns.append(
                Transaction(
                    date=datetime.strptime(row[date_col], date_fmt).date(),
                    description=row[desc_col],
                    amount=amount,
                    account=account,
                    source_file=path.name,
                    source_line=line,
                )
            )
        return txns
