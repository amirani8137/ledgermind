from datetime import date
from decimal import Decimal

from ledgermind import ledger
from ledgermind.cli import main
from ledgermind.models import Posting, Transaction
from ledgermind.pipeline import run_import
from ledgermind.writer import render


def test_end_to_end_import(workspace):
    s = run_import(workspace / "config.toml")
    assert s.files == 3
    assert s.new == 23
    assert s.needs_review == 3  # mortgage split, Amazon, unknown merchant
    assert not s.rejected and not s.errors
    assert s.in_transit == 0  # both sides of every transfer matched

    entries, errors, _ = ledger.load(workspace / "ledger" / "main.beancount")
    assert errors == []
    assert len(ledger.flagged(entries)) == 3


def test_reimport_is_idempotent(workspace):
    first = run_import(workspace / "config.toml")
    second = run_import(workspace / "config.toml")
    assert second.new == 0
    assert second.duplicates == first.new
    assert len(list((workspace / "ledger" / "imports").glob("import-*.beancount"))) == 1


def test_dry_run_writes_nothing(workspace):
    s = run_import(workspace / "config.toml", dry_run=True)
    assert s.new == 23 and s.output is None
    assert not list((workspace / "ledger" / "imports").glob("import-*"))


def test_history_categorizer_used(workspace):
    run_import(workspace / "config.toml")
    text = next((workspace / "ledger" / "imports").glob("import-*.beancount")).read_text()
    chevron = text[text.index('"CHEVRON 0091"') :].split("\n\n")[0]
    assert "history" in chevron and "Expenses:Auto:Fuel" in chevron


def test_invalid_output_is_quarantined(workspace, monkeypatch):
    from ledgermind import pipeline

    def bad_render(txn, threshold=0.8):  # writes to an account that was never opened
        return render(txn, threshold).replace("Expenses:Food:Groceries", "Expenses:Nope")

    monkeypatch.setattr(pipeline, "render", bad_render)
    s = run_import(workspace / "config.toml")
    assert s.rejected
    assert s.output.suffix == ".rejected"
    entries, errors, _ = ledger.load(workspace / "ledger" / "main.beancount")
    assert errors == []  # main ledger still clean


def test_writer_quotes_and_flags():
    t = Transaction(
        date(2026, 1, 1), 'Say "hi"', Decimal(-1), "Assets:A", counter_account="Expenses:B", confidence=0.5
    )
    out = render(t, 0.8)
    assert out.startswith('2026-01-01 ! "Say \\"hi\\""')
    t.postings = [Posting("Assets:S", Decimal(2), "XYZ", cost=Decimal(10))]
    t.confidence = 1.0
    assert "2 XYZ {10 USD}" in render(t)


def test_cli_commands(workspace, capsys, tmp_path):
    cfg = str(workspace / "config.toml")
    assert main(["import", "-c", cfg]) == 0
    assert main(["check", "-c", cfg]) == 0
    assert main(["review", "-c", cfg]) == 0
    assert "MORTGAGE" in capsys.readouterr().out
    out = tmp_path / "r.xlsx"
    assert main(["report", "-c", cfg, "-o", str(out)]) == 0
    assert out.exists()
    assert main(["import", "-c", str(tmp_path / "missing.toml")]) == 2
