"""Command-line interface: `ledgermind <command>`."""

from __future__ import annotations

import argparse
import logging
import sys

from . import __version__, ledger
from .config import load_config
from .importers import available
from .pipeline import run_import


def cmd_import(args) -> int:
    s = run_import(args.config, dry_run=args.dry_run)
    print(f"Files read:        {s.files}")
    print(f"New transactions:  {s.new}")
    print(f"Already imported:  {s.duplicates}")
    print(f"Need review:       {s.needs_review}")
    if s.output:
        print(f"Written to:        {s.output}")
    if args.dry_run:
        print("(dry run: nothing written)")
    if s.rejected:
        print("\nValidation FAILED. The new entries were quarantined (.rejected):")
        for e in s.errors:
            print(f"  {e}")
        return 1
    if s.in_transit:
        print(f"\nNote: {ledger.IN_TRANSIT} = {s.in_transit}. Some transfers are")
        print("still missing their other side (import the matching statement).")
    if s.needs_review:
        print("\nRun `ledgermind review` to see entries that need your attention.")
    return 0


def cmd_check(args) -> int:
    cfg = load_config(args.config)
    entries, errors, _ = ledger.load(cfg.ledger)
    for e in errors:
        print(ledger.format_error(e))
    print(
        f"{len(entries)} entries, {len(errors)} errors, "
        f"{len(ledger.flagged(entries))} flagged for review, "
        f"in-transit balance {ledger.in_transit_balance(entries)}"
    )
    return 1 if errors else 0


def cmd_review(args) -> int:
    cfg = load_config(args.config)
    entries, _, _ = ledger.load(cfg.ledger)
    items = ledger.flagged(entries)
    if not items:
        print("Nothing to review.")
        return 0
    for e in items:
        first = e.postings[0]
        amount = f"{first.units.number} {first.units.currency}" if first.units else ""
        other = ", ".join(p.account for p in e.postings[1:])
        print(f"{e.date}  {amount:>14}  {e.narration[:40]:<40}  -> {other}")
        print(f"{'':12}{e.meta.get('filename')}:{e.meta.get('lineno')}")
    print(
        f"\n{len(items)} entries need review. Edit the account in the file shown "
        "(or in Fava) and change '!' to '*'."
    )
    return 0


def cmd_report(args) -> int:
    try:
        from .reports.excel import build_report
    except ImportError:
        print('Excel reports need openpyxl: pip install "ledgermind[excel]"')
        return 1
    cfg = load_config(args.config)
    entries, errors, options = ledger.load(cfg.ledger)
    currency = (options.get("operating_currency") or ["USD"])[0]
    try:
        out = build_report(entries, args.output, currency)
    except ImportError:
        print('Excel reports need openpyxl: pip install "ledgermind[excel]"')
        return 1
    print(f"Report written to {out}")
    return 0


def cmd_importers(args) -> int:
    print("\n".join(available()))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ledgermind", description="AI-assisted personal accounting on Beancount"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, func, help_):
        p = sub.add_parser(name, help=help_)
        p.add_argument("-c", "--config", default="config.toml", help="path to config.toml")
        p.set_defaults(func=func)
        return p

    add("import", cmd_import, "import new statements from the inbox").add_argument(
        "--dry-run", action="store_true", help="show what would be imported without writing"
    )
    add("check", cmd_check, "validate the ledger")
    add("review", cmd_review, "list entries flagged for review")
    add("report", cmd_report, "write an Excel report").add_argument("-o", "--output", default="report.xlsx")
    sub.add_parser("importers", help="list available importers").set_defaults(func=cmd_importers)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s"
    )
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
