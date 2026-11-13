"""Typed, immutable values used by the detector and explainer boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class Transaction:
    txn_id: str
    account_id: str
    counterparty: str
    amount: Decimal
    direction: str
    timestamp: datetime
    channel: str


@dataclass(frozen=True)
class DetectionConfig:
    reporting_threshold: Decimal
    rolling_window_hours: int
    min_transaction_count: int

    @property
    def rolling_window(self) -> timedelta:
        return timedelta(hours=self.rolling_window_hours)


@dataclass(frozen=True)
class EvidenceTransaction:
    """A detector-selected transaction, deliberately smaller than raw input."""

    txn_id: str
    amount: Decimal
    timestamp: datetime

    def to_dict(self) -> dict[str, str]:
        return {
            "txn_id": self.txn_id,
            "amount": str(self.amount),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class FindingEvidence:
    """Authoritative, fully deterministic proof of one qualifying episode."""

    account_id: str
    finding_type: str
    transaction_count: int
    combined_amount: Decimal
    reporting_threshold: Decimal
    window_start: datetime
    window_end: datetime
    window_hours: Decimal
    transactions: tuple[EvidenceTransaction, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "account_id": self.account_id,
            "finding_type": self.finding_type,
            "transaction_count": self.transaction_count,
            "combined_amount": str(self.combined_amount),
            "reporting_threshold": str(self.reporting_threshold),
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "window_hours": str(self.window_hours),
            "transactions": [transaction.to_dict() for transaction in self.transactions],
        }

    def to_llm_payload(self) -> dict[str, object]:
        """The only payload that may cross from deterministic code to the LLM."""
        return self.to_dict()
