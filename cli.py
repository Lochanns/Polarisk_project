"""CLI orchestration. Detection remains usable without any LLM credentials."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .detector import detect_structuring
from .explainer import GroqNarrativeClient, explain_finding
from .parsing import load_config, load_transactions


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect transaction structuring from a CSV.")
    parser.add_argument("--transactions", default="data/transactions.csv", help="Path to transactions.csv")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--output", default="findings.json", help="Path for JSON findings")
    parser.add_argument("--explain", action="store_true", help="Generate Groq analyst narratives")
    parser.add_argument(
        "--api-key",
        help="Groq API key for --explain (defaults to the GROQ_API_KEY environment variable)",
    )
    args = parser.parse_args()

    findings = detect_structuring(load_transactions(args.transactions), load_config(args.config))
    client = GroqNarrativeClient(api_key=args.api_key) if args.explain else None
    output_findings = []
    for finding in findings:
        result = {"evidence": finding.to_dict()}
        if client is not None:
            result["analyst_narrative_non_authoritative"] = explain_finding(finding, client)
        output_findings.append(result)

    output = {
        "finding_count": len(output_findings),
        "findings": output_findings,
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
