"""Rule-based categorizer driven by a TOML file.

Example rules.toml:

  [[rule]]
  pattern = "WHOLE FOODS|TRADER JOE"      # case-insensitive regex
  account = "Expenses:Food:Groceries"

  [[rule]]
  pattern = "PAYROLL"
  account = "Income:Salary"
  direction = "credit"                     # optional: "debit" (money out) or "credit" (money in)

The first matching rule wins.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ..models import Transaction


@dataclass
class Rule:
    pattern: re.Pattern[str]
    account: str
    direction: str | None = None

    def matches(self, txn: Transaction) -> bool:
        if self.direction == "debit" and txn.amount >= 0:
            return False
        if self.direction == "credit" and txn.amount <= 0:
            return False
        return bool(self.pattern.search(f"{txn.payee or ''} {txn.description}"))


class RulesCategorizer:
    name = "rules"

    def __init__(self, rules: list[Rule]):
        self.rules = rules

    @classmethod
    def from_file(cls, path: Path) -> RulesCategorizer:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        rules = []
        for i, r in enumerate(data.get("rule", []), 1):
            try:
                rules.append(Rule(re.compile(r["pattern"], re.IGNORECASE), r["account"], r.get("direction")))
            except (KeyError, re.error) as e:
                raise ValueError(f"{path}: rule #{i} is invalid: {e}") from None
        return cls(rules)

    def categorize(self, txn: Transaction) -> tuple[str, float] | None:
        for rule in self.rules:
            if rule.matches(txn):
                return rule.account, 1.0
        return None
