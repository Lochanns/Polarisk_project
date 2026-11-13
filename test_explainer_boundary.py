from datetime import datetime
from decimal import Decimal

import pytest

from polarisk_detector.explainer import GroqNarrativeClient, explain_finding
from polarisk_detector.models import EvidenceTransaction, FindingEvidence


class RecordingClient:
    def __init__(self) -> None:
        self.payload = None

    def create_narrative(self, evidence_payload: dict[str, object]) -> str:
        self.payload = evidence_payload
        return "A neutral narrative based on the provided evidence."


def test_explainer_receives_only_computed_evidence_payload():
    timestamp = datetime(2026, 1, 1, 8, 0)
    evidence = FindingEvidence(
        account_id="A",
        finding_type="structuring",
        transaction_count=3,
        combined_amount=Decimal("51000"),
        reporting_threshold=Decimal("50000"),
        window_start=timestamp,
        window_end=timestamp,
        window_hours=Decimal("0"),
        transactions=(EvidenceTransaction("t1", Decimal("17000"), timestamp),),
    )
    client = RecordingClient()

    narrative = explain_finding(evidence, client)

    assert narrative.startswith("A neutral")
    assert set(client.payload) == {
        "account_id", "finding_type", "transaction_count", "combined_amount",
        "reporting_threshold", "window_start", "window_end", "window_hours", "transactions",
    }
    assert set(client.payload["transactions"][0]) == {"txn_id", "amount", "timestamp"}


def test_groq_client_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        GroqNarrativeClient()


def test_explicit_api_key_does_not_require_environment(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    # Construction should use the supplied key rather than the environment.
    # The network client is intentionally not exercised here.
    client = GroqNarrativeClient(api_key="test-key")

    assert client is not None
