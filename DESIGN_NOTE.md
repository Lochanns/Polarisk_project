# Design Note: Deterministic / LLM Architectural Boundary

## 1. The Deterministic / LLM Boundary

In anti-money laundering (AML) compliance, detection decisions must be mathematically verifiable, reproducible, and legally defensible. For this reason, the architecture enforces a strict, one-way boundary between deterministic detection logic and LLM-assisted narration.

### Detection (Authoritative)
All analytical computation is performed strictly by the deterministic detector (`detector.py`):
- Ingesting and validating transaction data using exact fixed-point arithmetic (`Decimal`).
- Filtering eligible transactions (credits strictly below the reporting threshold).
- Applying the sliding chronological window (`window_end - window_start <= rolling_window_hours`).
- Computing exact aggregated totals and verifying minimum transaction counts.
- Suppressing redundant alerts for continuous qualifying episodes.

The detector operates completely offline with zero dependency on external network calls or language models.

### Narrative Generation (Non-Authoritative)
The LLM is invoked solely as a formatting and communication layer for human analysts:
- **Strict Data Contract**: The LLM receives only a pre-computed `FindingEvidence` payload containing the flagged account ID, selected transaction IDs, amounts, timestamps, combined total, and window duration. It never receives raw transaction streams, debits, unflagged transactions, or transactions from other accounts.
- **No Analytical Agency**: The system prompt explicitly forbids the LLM from making detection decisions, calculating sums, recalculating windows, filtering transactions, or assuming motives.
- **Isolated Output**: Generated narratives are stored under the explicit key `analyst_narrative_non_authoritative`, ensuring that evidence remains pristine and untampered even if the LLM produces a stylistic irregularity.
- **Graceful Degradation**: If no Groq API key is configured or the LLM service is unavailable, detection runs at 100% functionality with full mathematical evidence.

---

## 2. Alternative Considered and Rejected: LLM-Based Detection

### The Alternative
An alternative architecture considered during initial design was a prompt-driven detector, where chronological account transaction histories (or CSV excerpts) would be passed directly to an LLM with instructions to identify potential structuring patterns and flag suspicious accounts.

### Why It Was Rejected
1. **Hallucination and Arithmetic Unreliability**: LLMs frequently make subtle arithmetic errors when summing multiple numbers and struggle with exact time-delta comparisons (such as whether a transaction occurred at hour 71:59 vs. 72:01). In AML compliance, flagging an innocent customer due to an arithmetic hallucination is unacceptable.
2. **Lack of Auditability and Reproducibility**: Regulatory scrutiny requires identical inputs to produce identical outputs every single time. LLM outputs are stochastic; the same transaction log evaluated twice could yield different findings.
3. **Cost, Latency, and Context Scaling**: Feeding raw transaction ledgers (thousands of rows) to an LLM incurs substantial token usage, high latency, and frequent rate-limiting, making batch processing impractical.
4. **Legal and Regulatory Defensibility**: Suspicious Activity Reports (SARs) require provable evidence. A compliance officer cannot defend an alert based on an LLM's hidden weights; they can defend an alert backed by exact timestamps, explicit thresholds, and deterministic code.

