from datetime import date
from decimal import Decimal

import pytest

from ledgermind.importers import available, get_importer, parse_amount
from tests.conftest import STATEMENTS


def test_registry_lists_builtin_importers():
    assert {"chase", "etrade", "generic_csv"} <= set(available())


def test_unknown_importer_message():
    with pytest.raises(KeyError, match="Available"):
        get_importer("nope")


@pytest.mark.parametrize(
    "text,expected",
    [("$1,234.56", "1234.56"), ("-12.00", "-12.00"), ("(7.50)", "-7.50"), ("", "0")],
)
def test_parse_amount(text, expected):
    assert parse_amount(text) == Decimal(expected)


def test_chase():
    txns = get_importer("chase").extract(
        STATEMENTS / "chase_checking_2026-01.csv", "Assets:Bank:Chase:Checking", {}
    )
    assert len(txns) == 11
    first = txns[0]
    assert first.date == date(2026, 1, 2)
    assert first.amount == Decimal("6500.00")
    assert first.source_line == 2


def test_generic_csv_negates_card_charges():
    txns = get_importer("generic_csv").extract(
        STATEMENTS / "amex_2026-01.csv", "Liabilities:CreditCard:Amex:Platinum", {"negate": True}
    )
    assert txns[0].amount == Decimal("-64.99")  # charge increases the liability
    assert txns[3].amount == Decimal("1240.55")  # payment reduces it


def test_generic_csv_debit_credit_columns(tmp_path):
    f = tmp_path / "bank.csv"
    f.write_text("Date,Memo,Debit,Credit\n2026-02-01,Coffee,4.50,\n2026-02-02,Refund,,10.00\n")
    txns = get_importer("generic_csv").extract(
        f,
        "Assets:Bank:X",
        {
            "description_column": "Memo",
            "debit_column": "Debit",
            "credit_column": "Credit",
            "date_format": "%Y-%m-%d",
        },
    )
    assert [t.amount for t in txns] == [Decimal("-4.50"), Decimal("10.00")]


def _balance(postings):
    """Sum of postings at cost, ignoring auto-balanced legs."""
    total = Decimal(0)
    for p in postings:
        if p.units is None or p.cost_empty:
            continue
        total += p.units * p.cost if p.cost is not None else p.units
    return total


def test_etrade_trades():
    txns = get_importer("etrade").extract(STATEMENTS / "etrade_2026-01.csv", "Assets:Brokerage:Etrade", {})
    by_type = {t.description.split()[0]: t for t in txns}

    buy = next(t for t in txns if "AAPL" in t.description and t.postings)
    assert _balance(buy.postings) == 0  # 5 x 230 + 0.65 commission == 1150.65 cash
    assert buy.postings[0].account == "Assets:Brokerage:Etrade:Stocks"

    sell = next(t for t in txns if t.description.startswith("Sold"))
    assert sell.postings[0].cost_empty and sell.postings[0].price == Decimal("155.00")
    assert sell.postings[-1].units is None  # gain computed by Beancount

    assert by_type["Dividend"].counter_account == "Income:Investments:Dividends:Ordinary"
    assert all(t.confidence == 1.0 for t in txns)
