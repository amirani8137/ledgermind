# Contributing to ledgermind

Thanks for helping! Whether you add support for your bank, fix a bug, improve
the docs or share accounting know-how, it all makes personal finance easier for
everyone.

## Golden rule: no real financial data

Never include real statements, account numbers, names or balances in issues,
pull requests, tests or screenshots. Create **fake** sample files that keep the
*format* of the real export (same columns, date style and quirks) with made-up
values.

## Development setup

```bash
git clone https://github.com/<you>/ledgermind.git
cd ledgermind
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest            # all tests should pass
ruff check .      # lint
ruff format .     # format
```

## Adding an importer (best first contribution)

1. **Create a fake sample** in `examples/statements/`, e.g.
   `wellsfargo_checking_2026-01.csv`, matching the real export's layout.

2. **Write the importer** in `ledgermind/importers/wellsfargo.py`:

   ```python
   from datetime import datetime
   from pathlib import Path
   from typing import Any

   from ..models import Transaction
   from .base import Importer, parse_amount, read_csv_rows, register


   @register
   class WellsFargoImporter(Importer):
       """Wells Fargo checking CSV (describe the export and header here)."""

       name = "wellsfargo"

       def extract(self, path: Path, account: str, options: dict[str, Any]) -> list[Transaction]:
           return [
               Transaction(
                   date=datetime.strptime(row["Date"], "%m/%d/%Y").date(),
                   description=row["Description"],
                   amount=parse_amount(row["Amount"]),  # negative = money out
                   account=account,
                   source_file=path.name,
                   source_line=line,
               )
               for line, row in read_csv_rows(path)
           ]
   ```

   Rules of thumb:
   - `amount` is signed from the account's point of view (for a credit card,
     a charge is negative).
   - Keep `source_file` / `source_line`: that's the audit trail.
   - For trades or splits, build `postings` yourself (see `etrade.py`) and set
     `confidence = 1.0`.
   - If the format is simple, consider whether `generic_csv` options already
     cover it, and document that instead.

3. **Register it**: add the module to the import line in
   `ledgermind/importers/__init__.py`.

4. **Test it** in `tests/test_importers.py`: count, a date, an amount, the sign.

5. **Document it**: add a row to the "Supported institutions" table in README.md.

## Other contributions

- **Categorization rules**: common merchant patterns for `examples/rules.toml`.
- **Accounting logic**: options, loans, wash sales, multi-currency. Please explain
  the accounting treatment in the PR description; reviewers may not be accountants.
- **Docs and translations**: always welcome.

## Pull request checklist

- [ ] Tests added or updated, and `pytest` passes
- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] No real personal or financial data anywhere
- [ ] README / docs updated if behavior changed

Small, focused PRs are reviewed fastest. For bigger changes, open an issue first
to agree on the approach.

## Code of conduct

By participating you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
