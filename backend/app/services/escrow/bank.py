from typing import Protocol

from sqlalchemy import select

from app.core.config import settings
from app.models.escrow import BankMockLedger


class BankPort(Protocol):
    def open_escrow(self, deal_id, amount_paisa: int, key: str) -> None: ...
    def deposit(self, deal_id, amount_paisa: int, key: str) -> None: ...
    def release(self, deal_id, amount_paisa: int, key: str) -> None: ...
    def refund(self, deal_id, amount_paisa: int, key: str) -> None: ...
    def balances(self, deal_id) -> dict[str, int]: ...


class MockBank:
    def __init__(self, db):
        self.db = db

    def _record(self, deal_id, operation, amount_paisa, key):
        prior = self.db.scalar(select(BankMockLedger).where(BankMockLedger.idempotency_key == key))
        if prior:
            return
        self.db.add(
            BankMockLedger(
                deal_id=deal_id, idempotency_key=key, operation=operation, amount_paisa=amount_paisa
            )
        )
        self.db.flush()

    def open_escrow(self, deal_id, amount_paisa, key):
        self._record(deal_id, "open", amount_paisa, key)

    def deposit(self, deal_id, amount_paisa, key):
        self._record(deal_id, "deposit", amount_paisa, key)

    def release(self, deal_id, amount_paisa, key):
        self._record(deal_id, "release", amount_paisa, key)

    def refund(self, deal_id, amount_paisa, key):
        self._record(deal_id, "refund", amount_paisa, key)

    def balances(self, deal_id):
        rows = self.db.scalars(
            select(BankMockLedger).where(BankMockLedger.deal_id == deal_id)
        ).all()
        escrow = buyer = seller = 0
        for row in rows:
            if row.operation == "deposit":
                escrow += row.amount_paisa
            elif row.operation == "refund":
                escrow -= row.amount_paisa
                buyer += row.amount_paisa
            elif row.operation == "release":
                escrow -= row.amount_paisa
                seller += row.amount_paisa
        return {"buyer_paisa": buyer, "escrow_paisa": escrow, "seller_paisa": seller}


def get_bank(db) -> BankPort:
    if settings.bank_provider != "mock":
        raise RuntimeError("Unsupported BANK_PROVIDER")
    return MockBank(db)
