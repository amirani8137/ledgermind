"""Optional LLM categorizer.

Providers:
  - "ollama"    : a local model (nothing leaves your computer). Default URL
                  http://localhost:11434
  - "anthropic" : Claude via the Anthropic API. Needs `pip install anthropic`
                  and the ANTHROPIC_API_KEY environment variable.

Privacy: only the date, amount and description of one transaction are sent,
plus the list of your category account names. Never balances or account
numbers.

The model must pick an account from your chart of accounts; anything else is
rejected. Low-confidence answers go to the review queue.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request

from ..models import Transaction

log = logging.getLogger(__name__)

PROMPT = """You are a careful bookkeeping assistant. Pick the single best account \
for this transaction from the list below.

Accounts:
{accounts}

Transaction:
  date: {date}
  amount: {amount} {currency}  (negative = money leaving the account)
  description: {description}

Reply with JSON only, no other text:
{{"account": "<exactly one account from the list>", "confidence": <number from 0 to 1>}}"""


class LLMCategorizer:
    name = "llm"

    def __init__(
        self,
        provider: str,
        model: str,
        accounts: list[str],
        base_url: str | None = None,
        timeout: float = 60,
    ) -> None:
        if provider not in ("ollama", "anthropic"):
            raise ValueError(f"Unknown LLM provider '{provider}' (use 'ollama' or 'anthropic')")
        self.provider = provider
        self.model = model
        self.accounts = sorted(accounts)
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.timeout = timeout
        self._client = None

    def categorize(self, txn: Transaction) -> tuple[str, float] | None:
        prompt = PROMPT.format(
            accounts="\n".join(self.accounts),
            date=txn.date.isoformat(),
            amount=txn.amount,
            currency=txn.currency,
            description=txn.description,
        )
        try:
            reply = self._complete(prompt)
        except Exception as e:  # network down, model missing, bad key...
            log.warning("LLM categorization failed (%s); leaving for review", e)
            return None
        return self._parse(reply)

    def _parse(self, reply: str) -> tuple[str, float] | None:
        match = re.search(r"\{.*\}", reply, re.DOTALL)
        if not match:
            return None
        try:
            obj = json.loads(match.group(0))
            account = str(obj["account"]).strip()
            confidence = max(0.0, min(1.0, float(obj.get("confidence", 0))))
        except (ValueError, KeyError, TypeError):
            return None
        if account not in self.accounts:
            return None
        return account, confidence

    def _complete(self, prompt: str) -> str:
        if self.provider == "ollama":
            body = json.dumps(
                {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "format": "json",
                }
            ).encode()
            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())["message"]["content"]

        if self._client is None:
            import anthropic  # optional dependency

            self._client = anthropic.Anthropic()
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
