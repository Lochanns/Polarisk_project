# Polarisk Transaction Pattern Detector

Deterministic detector for possible **structuring**: several credits below a
reporting threshold, from the same account, inside a rolling window, whose
combined amount exceeds the threshold.

The optional Groq explainer writes one analyst paragraph per finding. It only
sees evidence the detector already computed. It does not read the CSV, sum
amounts, choose transactions, or decide whether an account is flagged.

## Requirements

- Python 3.11+
- A Groq API key only when `--explain` is used

## Setup (under 5 minutes)

```bash
cd intern_project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Detection only (no API key):

```bash
python main.py
```

This reads `data/transactions.csv` and `config.json` and writes `findings.json`.

Add Groq narratives (one LLM call per finding):

```bash
export GROQ_API_KEY="your-key"
python main.py --explain
```

You can instead place `GROQ_API_KEY=your-key` in a local `.env` file; it is
automatically read when the command runs from the project directory. `.env` is
excluded from Git.

Alternatively, supply a key for a single run:

```bash
python main.py --explain --api-key "your-key"
```

The `--api-key` value takes precedence over `GROQ_API_KEY`. The key is never
read from `config.json` and is never written to output. Prefer the environment
variable for routine use so the key is not saved in shell history.

Custom paths:

```bash
python main.py \
  --transactions data/transactions.csv \
  --config config.json \
  --output findings.json
```

## Tests

```bash
pytest
```

## Rule implemented

For each account, a finding is raised when a chronological window contains at
least `min_transaction_count` **credit** transactions, each with amount strictly
less than `reporting_threshold`, such that:

```text
window_end - window_start <= rolling_window_hours
sum(amounts) > reporting_threshold
```

An amount exactly at the threshold is excluded. A combined total exactly at the
threshold is not flagged. A transaction exactly at the time-window boundary is
included. That last case is the deliberate edge-case test; see DECISIONS.md.

## Documentation and Design

- [DESIGN_NOTE.md](file:///Users/lochanns/Desktop/intern_project/DESIGN_NOTE.md): Explains the deterministic / LLM boundary and the alternative considered and rejected.
- [DECISIONS.md](file:///Users/lochanns/Desktop/intern_project/DECISIONS.md): Material engineering decisions, edge-case rationale, and AI assistance attribution.
- The JSON result stores detector evidence and `analyst_narrative_non_authoritative` in separate fields.

