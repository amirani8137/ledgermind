"""E*TRADE brokerage transaction CSV.

Expected header (E*TRADE transaction history download):
  TransactionDate,TransactionType,SecurityType,Symbol,Quantity,Amount,Price,Commission,Description

E*TRADE has changed its export layout over the years. If your file differs,
adjust the column names here or open an issue with a redacted sample.

`account` in config.toml is the brokerage root, e.g. "Assets:Brokerage:Etrade".
Cash goes to <root>:Cash and stock lots to <root>:Stocks.

Handled: Bought, Sold, Dividend, Interest, Transfer/Deposit/Withdrawal, Fee.
Anything else (options trades, corporate actions) is passed through as a
cash movement for the categorizer and usually lands in the review queue.
Options support is on the roadmap and a great contribution.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import Posting, Transaction
from .base import Importer, parse_amount, read_csv_rows, register

DEFAULTS = {
    "cash_account": "{root}:Cash",
    "stock_account": "{root}:Stocks",
    "commission_account": "Expenses:Investing:Commissions",
    "gains_account": "Income:Investments:CapitalGains",
    "dividend_account": "Income:Investments:Dividends:Ordinary",
    "interest_account": "Income:Investments:Interest:Brokerage",
    "fee_account": "Expenses:Investing:RegulatoryFees",
    "transfer_account": "Assets:Transfers:InTransit",
    "date_format": "%m/%d/%y",
}


@register
class EtradeImporter(Importer):
    name = "etrade"

    def extract(self, path: Path, account: str, options: dict[str, Any]) -> list[Transaction]:
        o = {**DEFAULTS, **options}
        cash = o["cash_account"].format(root=account)
        stocks = o["stock_account"].format(root=account)

        txns = []
        for line, row in read_csv_rows(path):
            ttype = row["TransactionType"].strip().lower()
            symbol = row.get("Symbol", "").strip().upper()
            qty = abs(parse_amount(row.get("Quantity")))
            amount = parse_amount(row["Amount"])
            price = parse_amount(row.get("Price"))
            commission = parse_amount(row.get("Commission"))
            desc = row.get("Description") or f"{row['TransactionType']} {symbol}".strip()

            t = Transaction(
                date=datetime.strptime(row["TransactionDate"], o["date_format"]).date(),
                description=f"{row['TransactionType']} {symbol} {desc}".strip() if symbol else desc,
                amount=amount,
                account=cash,
                payee="E*TRADE",
                source_file=path.name,
                source_line=line,
            )

            if ttype in ("bought", "buy") and symbol:
                t.postings = [Posting(stocks, qty, symbol, cost=price)]
                if commission:
                    t.postings.append(Posting(o["commission_account"], commission))
                t.postings.append(Posting(cash, amount))
                self._mark(t)
            elif ttype in ("sold", "sell") and symbol:
                t.postings = [
                    Posting(stocks, -qty, symbol, cost_empty=True, price=price),
                    Posting(cash, amount),
                ]
                if commission:
                    t.postings.append(Posting(o["commission_account"], commission))
                t.postings.append(Posting(o["gains_account"]))  # Beancount computes the gain
                self._mark(t)
            elif ttype == "dividend":
                self._mark(t, o["dividend_account"])
            elif ttype == "interest":
                self._mark(t, o["interest_account"])
            elif ttype in ("transfer", "deposit", "withdrawal"):
                self._mark(t, o["transfer_account"])
            elif ttype == "fee":
                self._mark(t, o["fee_account"])
            # else: left for the categorizer chain / review queue

            txns.append(t)
        return txns

    @staticmethod
    def _mark(t: Transaction, counter: str | None = None) -> None:
        if counter:
            t.counter_account = counter
        t.confidence = 1.0
        t.categorized_by = "importer"
