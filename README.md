# Verdict CLI

A real, working CLI for **deterministic, evidence-bound trust scoring of AI
agents** — the CWI Verdict Engine v1.0.0 as runnable software. Feed it evidence
JSON; get back a verdict: a score with a band and a full evidence trace, or an
honest refusal (`insufficient-data`, `evidence-disputed`, `unknown-context`,
`invalid-input`). It never invents a score.

Built by Cumulative Web Inc (CWI). Stdlib only — **zero dependencies, $0**.

## Install

You need Python 3.8+. Nothing else.

```bash
cd verdict-cli
python3 -m verdict_cli pin     # sanity check: vendored engine provenance
```

No `pip install`, no virtualenv, no API keys, no network. Ever.

## Quickstart — value in under 5 minutes

```bash
# 1. Get a valid input template (real-evidence shape, honest cold start)
python3 -m verdict_cli example > evidence.json

# 2. Score it — the honest answer for a new subject is insufficient-data
python3 -m verdict_cli score evidence.json --out ./run-001
```

You get:

```
  report.json: run-001/report.json
  report.md:   run-001/report.md
```

`report.json` is the canonical engine output (score or refusal, `input_sha256`
for reproducibility). `report.md` explains *why*: the evidence trace per
family, what was damped or not counted, exactly what is missing, and what to
do next.

Pipelines:

```bash
python3 -m verdict_cli check evidence.json
# MUSE_CWI | agent-trust | insufficient-data | verified evidence items: 1 found, 3 required ...

python3 -m verdict_cli spec     # the published scoring rules, plain text
```

## The scoring rules (no hidden weights)

- **Admission:** only `status: "verified"` evidence counts. `claimed`,
  `pending`, `refuted` count zero (listed, not counted). Any `disputed`
  item refuses the whole run.
- **Weight classes:** 1 = self-asserted · 2 = third-party attested ·
  3 = protocol/ledger-sealed.
- **Sybil damping:** one identity cluster keeps at most 2 verified items per
  family; self-asserted items count at 0.5×. All damped items stay visible.
- **Score:** `kept_weight / (kept_weight + 3.0)` per family, then the mean
  over families with evidence — rounded to 3 decimals, banded
  (`established ≥ 0.80` … `negligible < 0.20`).
- **Gates:** `agent-trust` needs 3 verified items across 2 families including
  ERC-8004 · `music-review` needs music-domain evidence · `payments` needs
  identity + commercial history.
- **Determinism:** no clock, no randomness, no network — same input gives
  byte-identical output, bound by `input_sha256`.

Full reference: `python3 -m verdict_cli spec`.

## The engine is vendored, not rewritten

`verdict_cli/_engine.py` is the canonical CWI Verdict Engine copied **verbatim**
from `CumulativeWebInc/cwi-learn` (branch `needs/verdict-engine`,
`trust/engine.py`, blob `e34b722e…29953`, pinned 2026-09-17). Weights,
thresholds, and gates are spec-versioned — the CLI never edits them. Run
`python3 -m verdict_cli pin` to audit the provenance; the test suite asserts
the vendored file's sha256 so any edit fails loudly.

## Provenance anchoring

A scored verdict is labeled `anchored` only if your input carries an
`anchor_ref` (evidence content pinned at scoring time, e.g. a timestamped
hash). Otherwise it is honestly labeled `unanchored` — verified on a
snapshot, source stability not pinned. Not a penalty; a description.

## Running the tests

```bash
python3 -m unittest discover -s tests
```

40 tests, all passing: vendored-file integrity pin, determinism
(byte-identical reruns, recomputable `input_sha256`), scoring math, Sybil
damping, all four refusal statuses, band boundaries, context gates, CLI
end-to-end (every subcommand, exit codes, stdin, malformed input), and
report rendering. Test fixtures are synthetic and labeled as such — they
verify math, never pose as evidence.

## HONESTY

Read this before you trust a score.

- **This tool scores evidence; it does not create trust.** Every number
  traces to the evidence items in your input. Garbage evidence in, garbage
  score out.
- **`insufficient-data` is the correct answer for new subjects** — not a
  failure. It is listed first-class because cold starts are the norm, not
  the exception.
- **There is deliberately no "scored" example template.** A scored example
  would require fabricated evidence, and this tool never fabricates
  evidence. Add real, citable evidence and the gate opens on its own.
- **Bands describe evidence depth, not character.** A `thin` score means
  sparse evidence, not a bad agent.
- **No telemetry, no network, no accounts.** Your evidence never leaves your
  machine.

## Layout

```
verdict-cli/
├── verdict_cli/
│   ├── __init__.py      public API: score_input, explain, spec_text, example_input
│   ├── __main__.py      python -m verdict_cli entry point
│   ├── _engine.py       canonical engine v1.0.0, vendored verbatim (DO NOT EDIT)
│   ├── cli.py           argparse CLI (score / check / example / spec / pin)
│   └── report.py        report.md + report.json writers
├── examples/
│   ├── insufficient.json  real-evidence template -> insufficient-data
│   └── disputed.json      template -> evidence-disputed
├── tests/               40 tests
├── README.md
└── PRODUCT.md
```

## License

Proprietary — Cumulative Web Inc. All rights reserved.
