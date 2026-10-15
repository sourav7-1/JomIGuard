"""Daily LLM spend guard, kept in a small JSON file: {"date": "YYYY-MM-DD", "spent_usd": "..."}."""

import json
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path

MTOK = Decimal(1_000_000)


class BudgetExceeded(RuntimeError):
    """The call would take today's LLM spend over LLM_DAILY_BUDGET_USD."""


def cost_usd(
    input_tokens: int, output_tokens: int, price_in: Decimal, price_out: Decimal
) -> Decimal:
    """Tokens x price per million tokens."""
    return (input_tokens * price_in + output_tokens * price_out) / MTOK


class Budget:
    def __init__(
        self, path: Path, daily_limit_usd: Decimal, today: Callable[[], date] = date.today
    ) -> None:
        self.path, self.limit, self.today = Path(path), Decimal(daily_limit_usd), today

    def spent_today(self) -> Decimal:
        if not self.path.exists():
            return Decimal(0)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return (
            Decimal(data["spent_usd"])
            if data.get("date") == self.today().isoformat()
            else Decimal(0)
        )

    def check(self, estimate_usd: Decimal) -> None:
        spent = self.spent_today()
        if spent + estimate_usd > self.limit:
            raise BudgetExceeded(
                f"LLM budget: spent {spent:.4f} + estimated {estimate_usd:.4f} USD "
                f"> daily limit {self.limit} USD"
            )

    def add(self, cost: Decimal) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"date": self.today().isoformat(), "spent_usd": str(self.spent_today() + cost)}
        self.path.write_text(json.dumps(data) + "\n", encoding="utf-8", newline="\n")
