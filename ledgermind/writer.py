"""Render transactions as Beancount text."""

from __future__ import annotations

from .models import Posting, Transaction


def _q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_posting(p: Posting) -> str:
    if p.units is None:
        return f"  {p.account}"
    line = f"  {p.account}  {p.units} {p.currency}"
    if p.cost_empty:
        line += " {}"
    elif p.cost is not None:
        line += f" {{{p.cost} {p.cost_currency}}}"
    if p.price is not None:
        line += f" @ {p.price} {p.price_currency}"
    return line


def render(txn: Transaction, review_threshold: float = 0.8) -> str:
    flag = "!" if txn.needs_review(review_threshold) else "*"
    header = f"{txn.date.isoformat()} {flag}"
    if txn.payee:
        header += f" {_q(txn.payee)}"
    header += f" {_q(txn.description)}"

    lines = [header]
    if txn.import_id:
        lines.append(f"  import_id: {_q(txn.import_id)}")
    if txn.source_file:
        lines.append(f"  source: {_q(f'{txn.source_file}:{txn.source_line}')}")
    if txn.categorized_by:
        lines.append(f"  categorized_by: {_q(f'{txn.categorized_by} ({txn.confidence:.2f})')}")

    postings = txn.postings or [
        Posting(txn.account, txn.amount, txn.currency),
        Posting(txn.counter_account or "Expenses:Uncategorized"),
    ]
    lines.extend(render_posting(p) for p in postings)
    return "\n".join(lines) + "\n"
