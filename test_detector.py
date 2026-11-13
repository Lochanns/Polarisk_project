from datetime import datetime, timedelta
from decimal import Decimal

from polarisk_detector.detector import detect_structuring
from polarisk_detector.models import DetectionConfig, Transaction


CONFIG = DetectionConfig(Decimal("50000"), rolling_window_hours=72, min_transaction_count=3)
START = datetime(2026, 1, 1, 8, 0)


def transaction(txn_id: str, amount: str, hours: int, *, account: str = "A", direction: str = "credit") -> Transaction:
    return Transaction(txn_id, account, "CP", Decimal(amount), direction, START + timedelta(hours=hours), "NEFT")


def test_flags_eligible_credits_above_threshold_with_exact_evidence():
    findings = detect_structuring([
        transaction("t3", "17000", 24), transaction("t1", "17000", 0), transaction("t2", "17000", 12)
    ], CONFIG)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.account_id == "A"
    assert finding.combined_amount == Decimal("51000")
    assert [item.txn_id for item in finding.transactions] == ["t1", "t2", "t3"]


def test_individual_amount_equal_to_threshold_is_not_eligible():
    findings = detect_structuring([transaction("t1", "50000", 0), transaction("t2", "50000", 1), transaction("t3", "50000", 2)], CONFIG)
    assert findings == []


def test_combined_amount_equal_to_threshold_is_not_flagged():
    findings = detect_structuring([transaction("t1", "17000", 0), transaction("t2", "17000", 1), transaction("t3", "16000", 2)], CONFIG)
    assert findings == []


def test_exact_72_hour_boundary_is_included():
    """Deliberate edge case: a credit exactly 72 hours later stays in the window."""
    findings = detect_structuring([transaction("t1", "17000", 0), transaction("t2", "17000", 36), transaction("t3", "17000", 72)], CONFIG)
    assert len(findings) == 1
    assert findings[0].window_hours == Decimal("72")


def test_transaction_after_72_hour_boundary_is_excluded():
    findings = detect_structuring([transaction("t1", "17000", 0), transaction("t2", "17000", 36), transaction("t3", "17000", 73)], CONFIG)
    assert findings == []


def test_debits_and_above_threshold_credits_do_not_create_structuring_evidence():
    transactions = [
        transaction("d1", "30000", 0, direction="debit"),
        transaction("d2", "30000", 1, direction="debit"),
        transaction("big", "60000", 2),
        transaction("small-1", "10000", 3),
        transaction("small-2", "10000", 4),
    ]
    assert detect_structuring(transactions, CONFIG) == []


def test_distinct_qualifying_episodes_for_one_account_are_both_returned():
    transactions = [
        transaction("a1", "17000", 0), transaction("a2", "17000", 1), transaction("a3", "17000", 2),
        transaction("b1", "18000", 200), transaction("b2", "18000", 201), transaction("b3", "18000", 202),
    ]
    findings = detect_structuring(transactions, CONFIG)
    assert len(findings) == 2
    assert [[item.txn_id for item in finding.transactions] for finding in findings] == [["a1", "a2", "a3"], ["b1", "b2", "b3"]]


def test_output_is_invariant_to_input_order():
    transactions = [transaction("t3", "17000", 2), transaction("t1", "17000", 0), transaction("t2", "17000", 1)]
    assert detect_structuring(transactions, CONFIG) == detect_structuring(list(reversed(transactions)), CONFIG)


def test_transactions_from_different_accounts_are_not_combined():
    findings = detect_structuring([
        transaction("a1", "17000", 0, account="A"),
        transaction("a2", "17000", 1, account="A"),
        transaction("b1", "17000", 2, account="B"),
    ], CONFIG)
    assert findings == []


def test_below_minimum_transaction_count_is_not_flagged():
    findings = detect_structuring([
        transaction("t1", "26000", 0),
        transaction("t2", "26000", 1),
    ], CONFIG)
    assert findings == []
