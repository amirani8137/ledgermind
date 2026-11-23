# Security Policy

ledgermind handles personal financial data, so we take security and privacy
seriously.

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Instead, use
GitHub's private reporting: **Security → Report a vulnerability** on this
repository. Include steps to reproduce and the potential impact. Never include
real financial data.

We aim to acknowledge reports within 7 days.

## Scope

Examples of what we want to hear about:
- Personal data sent somewhere the user didn't configure (e.g. to an LLM)
- Statement contents or ledger data written to logs or temp files unexpectedly
- Malicious statement files that cause code execution or file writes outside
  the configured folders

## If you accidentally committed real data

Rotate anything sensitive, remove the file, and purge it from Git history
(e.g. with `git filter-repo`). Deleting it in a new commit is not enough: it
remains in the history.
