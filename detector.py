"""Pure deterministic sliding-window structuring detector."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from .models import DetectionConfig, EvidenceTransaction, FindingEvidence, Transaction


def detect_structuring(
    transactions: Iterable[Transaction], config: DetectionConfig
) -> list[FindingEvidence]:
    """Return one evidence record when each account episode first qualifies.

    Only credits strictly below the configured reporting threshold are eligible.
    The active window is inclusive of its time boundary. Overlapping qualifying
    windows are represented by one finding until the account becomes
    non-qualifying; a later independent episode receives another finding.
    """
    by_account: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        if (
            transaction.direction == "credit"
            and transaction.amount < config.reporting_threshold
        ):
            by_account[transaction.account_id].append(transaction)

    findings: list[FindingEvidence] = []
    for account_id in sorted(by_account):
        account_transactions = sorted(
            by_account[account_id], key=lambda transaction: (transaction.timestamp, transaction.txn_id)
        )
        findings.extend(_detect_account_episodes(account_id, account_transactions, config))
    return findings


def _detect_account_episodes(
    account_id: str,
    transactions: list[Transaction],
    config: DetectionConfig,
) -> list[FindingEvidence]:
    findings: list[FindingEvidence] = []
    left = 0
    running_total = Decimal("0")
    was_qualifying = False

    for right, transaction in enumerate(transactions):
        running_total += transaction.amount

        # Keep transactions exactly at the boundary: only remove when strictly older.
        while transaction.timestamp - transactions[left].timestamp > config.rolling_window:
            running_total -= transactions[left].amount
            left += 1

        active_transactions = transactions[left : right + 1]
        qualifies = (
            len(active_transactions) >= config.min_transaction_count
            and running_total > config.reporting_threshold
        )
        if qualifies and not was_qualifying:
            findings.append(_make_evidence(account_id, active_transactions, running_total, config))
        was_qualifying = qualifies

    return findings


def _make_evidence(
    account_id: str,
    transactions: list[Transaction],
    combined_amount: Decimal,
    config: DetectionConfig,
) -> FindingEvidence:
    start = transactions[0].timestamp
    end = transactions[-1].timestamp
    duration_seconds = Decimal(str((end - start).total_seconds()))
    return FindingEvidence(
        account_id=account_id,
        finding_type="structuring",
        transaction_count=len(transactions),
        combined_amount=combined_amount,
        reporting_threshold=config.reporting_threshold,
        window_start=start,
        window_end=end,
        window_hours=duration_seconds / Decimal("3600"),
        transactions=tuple(
            EvidenceTransaction(txn_id=transaction.txn_id, amount=transaction.amount, timestamp=transaction.timestamp)
            for transaction in transactions
        ),
    )
