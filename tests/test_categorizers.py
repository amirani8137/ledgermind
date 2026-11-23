import re
from datetime import date
from decimal import Decimal

from beancount import loader

from ledgermind.categorizers import HistoryCategorizer, LLMCategorizer, RulesCategorizer, categorize
from ledgermind.categorizers.history import normalize
from ledgermind.categorizers.rules import Rule
from ledgermind.models import UNCATEGORIZED, Transaction


def txn(desc, amount="-10.00"):
    return Transaction(date(2026, 1, 1), desc, Decimal(amount), "Assets:Bank:Checking")


def test_rules_first_match_and_direction():
    r = RulesCategorizer(
        [
            Rule(re.compile("PAYROLL", re.IGNORECASE), "Income:Salary", "credit"),
            Rule(re.compile("whole foods", re.IGNORECASE), "Expenses:Food:Groceries"),
        ]
    )
    assert r.categorize(txn("WHOLE FOODS #1")) == ("Expenses:Food:Groceries", 1.0)
    assert r.categorize(txn("PAYROLL", "-5")) is None  # wrong direction
    assert r.categorize(txn("PAYROLL", "100"))[0] == "Income:Salary"


def test_rules_from_example_file():
    from tests.conftest import EXAMPLES

    r = RulesCategorizer.from_file(EXAMPLES / "rules.toml")
    assert r.categorize(txn("NETFLIX.COM"))[0] == "Expenses:Entertainment:Subscriptions"


def test_normalize_strips_numbers():
    assert normalize("STARBUCKS STORE 05521") == "STARBUCKS STORE"


def test_history_learns_from_cleared_entries():
    entries, errors, _ = loader.load_string(
        """
2020-01-01 open Assets:Bank:Checking
2020-01-01 open Expenses:Auto:Fuel
2020-01-01 open Expenses:Uncategorized
2025-12-20 * "CHEVRON 0091"
  Assets:Bank:Checking  -50.00 USD
  Expenses:Auto:Fuel
2025-12-21 ! "SHELL 1"
  Assets:Bank:Checking  -40.00 USD
  Expenses:Auto:Fuel
"""
    )
    assert not errors
    h = HistoryCategorizer(entries)
    assert h.categorize(txn("CHEVRON 0123")) == ("Expenses:Auto:Fuel", 0.9)
    assert h.categorize(txn("SHELL 2")) is None  # "!" entries are not trusted yet


class FakeLLM(LLMCategorizer):
    def __init__(self, reply, accounts):
        super().__init__("ollama", "fake", accounts)
        self.reply = reply

    def _complete(self, prompt):
        return self.reply


def test_llm_accepts_only_known_accounts():
    accounts = ["Expenses:Shopping:Household", "Expenses:Food:Dining"]
    ok = FakeLLM('{"account": "Expenses:Shopping:Household", "confidence": 0.85}', accounts)
    assert ok.categorize(txn("AMAZON")) == ("Expenses:Shopping:Household", 0.85)
    made_up = FakeLLM('{"account": "Expenses:Made:Up", "confidence": 0.99}', accounts)
    assert made_up.categorize(txn("AMAZON")) is None
    garbage = FakeLLM("sorry, I can't", accounts)
    assert garbage.categorize(txn("AMAZON")) is None


def test_llm_failure_is_not_fatal():
    class Broken(LLMCategorizer):
        def _complete(self, prompt):
            raise ConnectionError("no server")

    assert Broken("ollama", "m", ["Expenses:X"]).categorize(txn("X")) is None


def test_chain_falls_back_to_uncategorized():
    t = txn("MYSTERY")
    categorize(t, [RulesCategorizer([])], {"Expenses:Food:Dining"})
    assert t.counter_account == UNCATEGORIZED and t.needs_review(0.8)


def test_chain_ignores_accounts_not_in_ledger():
    t = txn("WHOLE FOODS")
    r = RulesCategorizer([Rule(re.compile("WHOLE", re.IGNORECASE), "Expenses:Not:Opened")])
    categorize(t, [r], {"Expenses:Food:Groceries"})
    assert t.counter_account == UNCATEGORIZED
