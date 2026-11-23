# Architecture

```
            config.toml
                │
statements/ ──► Importer (per institution) ──► Transaction objects
                                                  │
                         existing ledger ──► dedupe by import_id
                                                  │
                    Categorizer chain: importer → rules → history → LLM → Uncategorized
                                                  │
                         Writer ──► ledger/imports/import-<timestamp>.beancount
                                                  │
                    Validate whole ledger (Beancount) ── errors? ──► rename to .rejected
```

## Modules

| Module | Responsibility |
|---|---|
| `models.py` | `Transaction` and `Posting`, the shared data model |
| `importers/` | One plugin per institution; `base.py` defines the interface and registry |
| `categorizers/` | `rules.py` (TOML regex), `history.py` (learns from cleared entries), `llm.py` (Ollama / Anthropic) |
| `writer.py` | Renders transactions as Beancount text with metadata |
| `ledger.py` | Loads and inspects the ledger (import IDs, open accounts, in-transit balance) |
| `pipeline.py` | Orchestrates an import run and returns a `Summary` |
| `reports/excel.py` | Excel income statement, balance sheet and review queue |
| `cli.py` | `ledgermind` command |

## Design principles

1. **The ledger is the source of truth.** It's plain text, versionable, and readable without this tool.
2. **AI suggests, accounting verifies.** Categories must be existing accounts, every
   transaction must balance, and the full ledger must validate before an import is kept.
3. **Cheap and predictable first.** Rules and history handle most transactions;
   the LLM only sees what's left.
4. **Human in the loop.** Uncertain entries are flagged `!`. Clearing them (`*`) is
   both the approval and the training signal for the history categorizer.
5. **Idempotent.** `import_id` = hash of account, date, amount, description and
   occurrence number, so the same statement can be imported any number of times.
6. **Transfers balance through `Assets:Transfers:InTransit`.** A non-zero balance
   means one side of a transfer hasn't been imported yet.

## Entry metadata

```beancount
2026-01-20 * "CHEVRON 0091"
  import_id: "17fe52f00bc0d7f4"           ; dedupe key
  source: "chase_checking_2026-01.csv:12" ; audit trail
  categorized_by: "history (0.90)"        ; which step decided, and how sure
  Assets:Bank:Chase:Checking  -58.40 USD
  Expenses:Auto:Fuel
```
