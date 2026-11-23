# ledgermind

**AI-assisted personal accounting on Beancount: statements in, balanced double-entry books out. Local-first and private.**

Drop your bank, credit card, loan and brokerage statements into a folder. ledgermind
reads them, categorizes every transaction, matches transfers between your own
accounts, and writes balanced entries into a [Beancount](https://github.com/beancount/beancount)
ledger. Anything it isn't sure about goes into a review queue instead of your books.

> Built by [Ajay Mirani](https://ajaymirani.com), Senior Manager, Software Engineering,
> and Deepa Menghani, Chartered Accountant / CPA. An engineer and an accountant who
> wanted personal books done properly: double-entry, auditable, private, and
> without retyping statements.

```
statements/  ──►  importers  ──►  dedupe  ──►  categorize  ──►  write  ──►  validate
 (CSV/PDF)        (per bank)      (import_id)   rules → history   .beancount   bean-check
                                                → LLM (optional)               or quarantine
```

## Why ledgermind?

- **Your books stay correct.** The AI only *suggests* categories. Every entry is
  double-entry and validated by Beancount; if a new batch would break the ledger,
  it is quarantined (`.rejected`) and your books are untouched.
- **Private by default.** Runs on your computer. The optional AI step can use a
  local model through [Ollama](https://ollama.com), so nothing leaves your machine.
  Claude (Anthropic API) is supported if you prefer.
- **Audit trail.** Every entry records the statement file and line it came from.
- **Learns from you.** Fix an entry once, mark it reviewed, and the same merchant
  is categorized automatically next month.
- **No double counting.** Transfers (checking → brokerage, card payments) go
  through an in-transit account, and ledgermind tells you if one side is missing.
- **Real-life accounts.** Checking, savings, credit cards, mortgage and car
  loans, and brokerage accounts with stock lots, cost basis and realized gains.
- **Plain text you own.** Works with [Fava](https://github.com/beancount/fava) for
  reports and charts, and with Git for full history of every change.

## Quick start (5 minutes, with fake data)

Requires Python 3.11+.

```bash
git clone https://github.com/amirani8137/ledgermind.git
cd ledgermind
pip install -e ".[excel,viewer]"

cd examples
ledgermind import          # reads statements/, writes ledger/imports/...
ledgermind review          # shows the 3 entries that need your attention
ledgermind report          # writes report.xlsx (income statement, balance sheet)
fava ledger/main.beancount   # browse it at http://localhost:5000
```

> **Windows:** if `ledgermind` or `fava` is "not recognized", pip installed them to a
> folder that isn't on your PATH. Use `python -m ledgermind import` or add the
> Python `Scripts` folder to PATH.

## Using it for your own accounts

1. **Create a private folder for your books (never inside a public repo).**
   Copy `examples/` there, then replace `ledger/accounts.beancount` with your own
   accounts. Start from [`templates/accounts.beancount`](templates/accounts.beancount).
2. **Edit `config.toml`**: one `[[sources]]` block per account, saying which
   importer reads it and which ledger account it belongs to.
3. **Add opening balances** to `ledger/main.beancount` from your latest statements.
4. **Write a few rules** in `rules.toml` for your regular merchants.
5. Each month: download statements into `statements/` and run `ledgermind import`.
   Then `ledgermind review`, fix anything flagged `!` and change it to `*`.

### Commands

| Command | What it does |
|---|---|
| `ledgermind import [--dry-run]` | Import new statements (re-running never duplicates) |
| `ledgermind review` | List entries flagged for review |
| `ledgermind check` | Validate the ledger; show the in-transit balance |
| `ledgermind report -o file.xlsx` | Excel: monthly income statement, balance sheet, review queue |
| `ledgermind importers` | List available importers |

All commands take `-c path/to/config.toml` (default: `./config.toml`).

### Optional AI categorization

```toml
[llm]
enabled  = true
provider = "ollama"       # local: install Ollama, then `ollama pull llama3.1`
model    = "llama3.1"
```

or, with `pip install "ledgermind[anthropic]"` and `ANTHROPIC_API_KEY` set:

```toml
[llm]
enabled  = true
provider = "anthropic"
model    = "claude-haiku-5-5"
```

Only the date, amount and description of a transaction are sent, plus your
category names. The model must choose an account that exists in your ledger;
low-confidence answers go to review.

## Supported institutions

| Importer | Covers |
|---|---|
| `chase` | Chase checking / savings CSV |
| `etrade` | E*TRADE brokerage transactions: buys, sells (FIFO lots), dividends, interest, transfers, fees |
| `generic_csv` | Any bank or card with a simple CSV (configurable columns, signed or debit/credit) |

**Your bank isn't listed?** Adding one is usually ~50 lines of Python and the
best first contribution. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

- [ ] PDF statement parsing
- [ ] Options trades (open/close, expiry, assignment) for E*TRADE, Schwab, Fidelity
- [ ] Loan payment splitting (principal / interest / escrow) from amortization schedules
- [ ] Importers: Schwab, Fidelity, Robinhood, Bank of America, Wells Fargo, Citi, Capital One
- [ ] Wash-sale detection and Form 8949 / Schedule D summaries
- [ ] Ask questions in plain English ("How much did I spend on dining in Q3?")
- [ ] Multi-currency and cross-border (US + India NRE/NRO, FBAR summaries)
- [ ] Review queue UI

See [docs/architecture.md](docs/architecture.md) for how the pieces fit together.

## Privacy and safety

- Never commit real statements or ledgers. The included `.gitignore` blocks
  statement files outside `examples/`, but keep your books in a separate private
  folder or repo anyway.
- Sample data in `examples/` is entirely made up.
- Found a security issue? See [SECURITY.md](SECURITY.md).

## Disclaimer

ledgermind is a bookkeeping tool. It is not tax, legal or investment advice.
Check important figures against your statements and consult a qualified
professional for tax filings.

## Authors

- **Ajay Mirani**, Senior Manager, Software Engineering, and AI/ML researcher
  working on intelligent financial systems.
  [ajaymirani.com](https://ajaymirani.com) ·
  [LinkedIn](https://www.linkedin.com/in/ajaymirani/) ·
  [Google Scholar](https://scholar.google.com/citations?user=6mVSIhsAAAAJ)
- **Deepa Menghani**, Chartered Accountant (CA) and Certified Public Accountant (CPA).

## License

[Apache 2.0](LICENSE). Contributions welcome!
