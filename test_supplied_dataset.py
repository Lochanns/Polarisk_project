from pathlib import Path

from polarisk_detector.detector import detect_structuring
from polarisk_detector.parsing import load_config, load_transactions

ROOT = Path(__file__).resolve().parents[1]


def test_supplied_dataset_flags_six_structuring_accounts():
    findings = detect_structuring(
        load_transactions(ROOT / "data" / "transactions.csv"),
        load_config(ROOT / "config.json"),
    )
    assert [finding.account_id for finding in findings] == [
        "ACC-1001",
        "ACC-1002",
        "ACC-1003",
        "ACC-1004",
        "ACC-1005",
        "ACC-1006",
    ]
