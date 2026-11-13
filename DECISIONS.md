# DECISIONS.md

This file explains the main decisions made while building the Polarisk transaction pattern detector, along with the reasoning behind them, edge cases, call volume handling, and AI agent usage. For the focused architectural breakdown of the deterministic/LLM boundary and alternatives rejected, see [DESIGN_NOTE.md](file:///Users/lochanns/Desktop/intern_project/DESIGN_NOTE.md).


## 1. Overall Approach

One of the first things I decided was to keep the actual detection logic completely independent of the LLM.

The detector handles everything related to identifying suspicious patterns, including filtering transactions, checking thresholds, calculating totals, evaluating time windows, and generating findings. All of this happens in `detector.py`.

The LLM comes into the picture only after the detector has identified a finding. It receives a `FindingEvidence` object containing the relevant transaction IDs, amounts, and timestamps. Its only job is to generate a short explanation of the finding.

I wanted to keep these two responsibilities separate because I don't think an LLM should be making the actual compliance decision. The output should be based on calculations and rules that can be tested and reproduced, rather than a model's interpretation.

The generated explanation is therefore stored separately in `analyst_narrative_non_authoritative`. It does not change the detector's output or its findings.

I also made sure that the application works without an API key. The `--explain` flag is optional, and the Groq client is initialized only when it is needed. The API key is read from the environment rather than being stored in the configuration file.

## LLM call volume

The explainer makes **one Groq call per finding**, after detection has finished.
The supplied dataset produces six findings, so `--explain` makes six calls. I did
not batch findings into a single prompt, because that would make it harder to
prove that the model only saw one evidence payload at a time.

If `--explain` is omitted, there are zero LLM calls and detection still runs.
That is how the project stays usable without a key, and how unit tests stay
offline.

## Deliberate edge case

The assignment asks for at least one deliberate edge-case test. I chose
**a credit that lands exactly 72 hours after the first credit in the window**
(`test_exact_72_hour_boundary_is_included`, with
`test_transaction_after_72_hour_boundary_is_excluded` as the counterpart).

I chose this case because the rolling-window rule is easy to get wrong: an
off-by-one on the comparison (`>` vs `>=`) either drops a legal deposit or
pulls in a deposit that is outside the configured hours. The implemented rule
is inclusive of the boundary (`window_end - window_start <= rolling_window_hours`).
A transaction one hour past 72 hours does not qualify.

## 2. Important Design Decisions

### Keep detection deterministic

I initially considered sending transaction data to Groq and asking it to identify possible structuring patterns.

I decided against this approach because it would make the most important part of the application dependent on an LLM. The results could vary between runs, and it would be difficult to explain exactly why a particular transaction was flagged.

Instead, I kept all detection decisions in Python. This also ensures that the LLM never gets access to the original CSV data.

### Avoid duplicate findings from overlapping windows

While implementing the sliding-window logic, I noticed that the same group of transactions could satisfy the detection conditions across multiple consecutive windows.

Reporting every qualifying window would create multiple alerts for what is essentially the same episode.

To avoid this, I implemented a one-finding-per-episode approach. Once an account enters a qualifying episode, the detector does not generate another finding until the account becomes non-qualifying and subsequently qualifies again.

I felt this was a more useful approach because it avoids unnecessary duplicate alerts.

### Use Decimal instead of float for monetary values

I chose `Decimal` for transaction amounts, combined totals, and threshold comparisons.

Using floating-point values for money can introduce precision issues. For example, calculations involving multiple decimal values may not produce the exact result expected.

I also paid attention to the boundary conditions:
- An individual transaction equal to the threshold is not considered eligible.
- A combined amount equal to the reporting threshold is not flagged.
- A transaction exactly at the time-window boundary is included.

These comparisons are implemented explicitly so that the results remain consistent.

### Pass only the required evidence to the LLM

I considered passing the complete transaction records to the explainer, but decided that most of that information was unnecessary once a finding had already been generated.

The `EvidenceTransaction` object therefore contains only:
- Transaction ID
- Amount
- Timestamp

The explainer does not have access to the CSV file or the detector itself. This makes the separation between detection and explanation easier to maintain.

### Keep the Groq integration separate

I did not want the tests to depend on an actual Groq API call. Apart from requiring an API key, this could also make tests slower, unreliable, and potentially expensive.

To avoid that, I introduced a `NarrativeClient` protocol. The explainer depends on this interface rather than directly depending on the Groq implementation.

For testing, I use a fake client that records the payload it receives. This allows me to verify that only the expected evidence is passed to the LLM.

The actual Groq integration is handled separately using its OpenAI-compatible API endpoint.

### Separate parsing, detection and explanation

I considered keeping the entire implementation in one module to make the initial development simpler.

However, separating the responsibilities made more sense, especially because I wanted to enforce the restriction on what the LLM can access.

The code is divided so that:
- Parsing is responsible for reading and validating the input files.
- Detection works with validated transaction data.
- Explanation works only with the evidence generated by the detector.

This also makes individual components easier to test and modify.

## 3. Use of AI Tools

I used an AI coding agent during development to help understand the assignment, inspect the supplied dataset, explore possible approaches, and prepare the initial implementation.

It also helped with drafting the tests, README, and this decision log.

I reviewed the proposed implementation rather than accepting everything as it was generated. In particular, I retained the use of `Decimal`, explicit timestamp sorting, sliding-window detection, and the evidence-only LLM interface.

I also made changes to the initial approach, particularly around handling overlapping qualifying windows. I added a separate fake-client test to verify that the explainer receives only the intended evidence.

I deliberately avoided approaches that would allow the LLM to make detection decisions or modify authoritative output fields.

## 4. Things I'm Not Completely Sure About

There are two areas where I think a different implementation could also be reasonable.

**Timestamp handling**

The timestamps in the supplied dataset are ISO-8601 strings without timezone offsets. For the current implementation, I treat them as naïve datetimes.

This works consistently with the supplied data, but for a production system, I would prefer to make the timezone explicit. Otherwise, timestamps from different timezones could cause incorrect time-window calculations.

**One finding per qualifying episode**

I chose to generate one finding when an episode first qualifies rather than generating an alert for every qualifying window.

I think this is a reasonable way to avoid duplicate alerts, but there are other possibilities. For example, the detector could report the window with the highest combined amount or report every maximal qualifying window.

I went with the current approach because it is straightforward, deterministic, and avoids repeatedly reporting the same activity.

## 5. Time Spent

I spent approximately six hours on the assignment.

- Around one hour understanding the requirements and inspecting the supplied data.
- Two to three hours working on the detector and its tests.
- Around one hour implementing the Groq integration and testing the evidence boundary.
- Around one hour on the README, documentation, and reviewing the implementation.

## 6. What I Would Improve With More Time

There are a few things I would like to improve if I had more time.

First, I would add JSON Schema validation for both the configuration and generated output so that invalid structures are caught early.

I would also make timestamp handling more explicit by introducing a clear timezone policy during parsing.

Finally, I would consider adding a deterministic severity score to help prioritize findings.

However, I would keep the core design unchanged. The actual detection should remain rule-based and independent of the LLM, with the model restricted to generating explanations for findings that have already been identified.