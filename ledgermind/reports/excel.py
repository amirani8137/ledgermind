"""Excel report: monthly income statement, balance sheet (at cost), review queue.

Requires the optional extra: pip install "ledgermind[excel]"
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from beancount.core import data


def _value(posting, currency: str) -> Decimal | None:
    """Posting value in the operating currency, using cost for lots."""
    if posting.units is None:
        return None
    cost = posting.cost
    if cost is not None and getattr(cost, "number", None) is not None:
        if cost.currency != currency:
            return None
        return posting.units.number * cost.number
    if posting.units.currency != currency:
        return None
    return posting.units.number


def build_report(entries, out: Path, currency: str = "USD") -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    monthly: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    balances: dict[str, Decimal] = defaultdict(Decimal)
    months: set[str] = set()

    for e in entries:
        if not isinstance(e, data.Transaction):
            continue
        month = e.date.strftime("%Y-%m")
        for p in e.postings:
            v = _value(p, currency)
            if v is None:
                continue
            if p.account.startswith(("Income:", "Expenses:")):
                monthly[p.account][month] += v
                months.add(month)
            else:
                balances[p.account] += v

    wb = Workbook()
    bold = Font(bold=True)
    money = "#,##0.00;[Red]-#,##0.00"

    # Income statement (income shown positive, expenses positive)
    ws = wb.active
    ws.title = "Income Statement"
    cols = sorted(months)
    ws.append(["Account", *cols, "Total"])
    for c in ws[1]:
        c.font = bold
    for section, sign in (("Income:", -1), ("Expenses:", 1)):
        ws.append([section.rstrip(":")])
        ws.cell(ws.max_row, 1).font = bold
        for acct in sorted(a for a in monthly if a.startswith(section)):
            vals = [float(sign * monthly[acct].get(m, 0)) for m in cols]
            ws.append([acct, *vals, sum(vals)])
    for row in ws.iter_rows(min_row=2, min_col=2):
        for c in row:
            c.number_format = money
    ws.column_dimensions["A"].width = 45

    # Balance sheet
    bs = wb.create_sheet("Balance Sheet")
    bs.append(["Account", f"Balance ({currency}, at cost)"])
    for c in bs[1]:
        c.font = bold
    totals = defaultdict(Decimal)
    for acct in sorted(a for a in balances if balances[a] != 0):
        root = acct.split(":")[0]
        totals[root] += balances[acct]
        bs.append([acct, float(balances[acct])])
    bs.append([])
    for root in ("Assets", "Liabilities"):
        bs.append([f"Total {root}", float(totals[root])])
        bs.cell(bs.max_row, 1).font = bold
    bs.append(["Net worth", float(totals["Assets"] + totals["Liabilities"])])
    bs.cell(bs.max_row, 1).font = bold
    for row in bs.iter_rows(min_row=2, min_col=2):
        for c in row:
            c.number_format = money
    bs.column_dimensions["A"].width = 45
    bs.column_dimensions["B"].width = 24

    # Review queue
    rv = wb.create_sheet("Needs Review")
    rv.append(["Date", "Description", "Amount", "Account", "Source"])
    for c in rv[1]:
        c.font = bold
    for e in entries:
        if isinstance(e, data.Transaction) and e.flag == "!":
            first = e.postings[0]
            rv.append(
                [
                    e.date.isoformat(),
                    e.narration,
                    float(first.units.number) if first.units else None,
                    first.account,
                    e.meta.get("source", ""),
                ]
            )
    rv.column_dimensions["B"].width = 45
    rv.column_dimensions["D"].width = 35

    out = Path(out)
    wb.save(out)
    return out
