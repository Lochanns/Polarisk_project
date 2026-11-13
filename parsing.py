"""File-boundary parsing and validation; no detection rules live here."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import DetectionConfig, Transaction

REQUIRED_COLUMNS = {
    "txn_id", "account_id", "counterparty", "amount", "direction", "timestamp", "channel"
}


def load_config(path: str | Path) -> DetectionConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        config = DetectionConfig(
            reporting_threshold=Decimal(str(raw["reporting_threshold"])),
            rolling_window_hours=int(raw["rolling_window_hours"]),
            min_transaction_count=int(raw["min_transaction_count"]),
        )
    except (KeyError, ValueError, InvalidOperation) as error:
        raise ValueError("Invalid detector configuration") from error

    if config.reporting_threshold <= 0:
        raise ValueError("reporting_threshold must be positive")
    if config.rolling_window_hours <= 0:
        raise ValueError("rolling_window_hours must be positive")
    if config.min_transaction_count <= 0:
        raise ValueError("min_transaction_count must be positive")
    return config


def load_transactions(path: str | Path) -> list[Transaction]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or set(reader.fieldnames) != REQUIRED_COLUMNS:
            raise ValueError(f"CSV columns must be exactly {sorted(REQUIRED_COLUMNS)}")

        transactions: list[Transaction] = []
        txn_ids: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            try:
                direction = row["direction"].strip().lower()
                if direction not in {"credit", "debit"}:
                    raise ValueError("direction must be credit or debit")
                transaction = Transaction(
                    txn_id=row["txn_id"].strip(),
                    account_id=row["account_id"].strip(),
                    counterparty=row["counterparty"].strip(),
                    amount=Decimal(row["amount"]),
                    direction=direction,
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    channel=row["channel"].strip(),
                )
            except (KeyError, ValueError, InvalidOperation) as error:
                raise ValueError(f"Invalid CSV row {row_number}") from error
            if not transaction.txn_id or transaction.txn_id in txn_ids:
                raise ValueError(f"txn_id must be unique; invalid value at row {row_number}")
            if (
                not transaction.account_id
                or not transaction.amount.is_finite()
                or transaction.amount <= 0
            ):
                raise ValueError(f"account_id and amount must be positive/non-empty at row {row_number}")
            txn_ids.add(transaction.txn_id)
            transactions.append(transaction)
    return transactions
