---
name: "trust-verdict"
description: "Score agent trust deterministically with the CWI Verdict Engine — evidence-bound scoring over ERC-8004, Needle Drop, and First Spin signals. Returns insufficient-data instead of inventing scores."
---

# Trust Verdict

## Purpose
Invoke the CWI Verdict Engine (v1.0.0): deterministic, evidence-bound trust
scoring for AI agents. It closes the three gaps ERC-8004 leaves open — score
aggregation, Sybil resistance, dispute resolution — with published rules.

**Hard rule:** the engine never invents a score. Insufficient evidence yields
`insufficient-data`; disputed evidence yields `evidence-disputed`. Present
those statuses as-is — never as a number.

## Tooling
`engine.py` (stdlib only — no dependencies) lives in the cwi-learn repo under
`trust/` (branch `needs/verdict-engine` until merged, then `main`). Fetch and
run it locally:

```bash
curl -sL https://raw.githubusercontent.com/CumulativeWebInc/cwi-learn/needs/verdict-engine/trust/engine.py -o /tmp/verdict-engine.py
# after merge, replace 'needs/verdict-engine' with 'main'
python3 /tmp/verdict-engine.py < input.json > output.json
```

Input contract (see `trust/spec.md` §3 for the full schema):

```json
{
  "engine_version": "1.0.0",
  "subject": { "agent_id": "MUSE_CWI", "display_name": "KingCode" },
  "context": "agent-trust",
  "observed_at": "2026-09-15T19:30:00Z",
  "signals": { "erc8004": [ ... ], "needle_drop": [ ... ], "first_spin": [ ... ] }
}
```

- Signal families: `erc8004` (on-chain identity), `needle_drop` (verified
  history — the ledger ships empty), `first_spin` (published verdicts only;
  worked examples and demo data are excluded).
- Evidence statuses: `verified` counts; `claimed`/`pending`/`refuted` count
  zero; `disputed` refuses the whole scoring run.
- Contexts: `agent-trust` (identity + corroboration), `music-review`
  (music-domain evidence required), `payments` (identity + commercial
  history required).

Output contract: `status` is `scored` | `insufficient-data` |
`evidence-disputed` | `unknown-context` | `invalid-input`. `score` is numeric
**only** when `status == "scored"`; otherwise it is `null` and `missing`
explains exactly what is absent. Every output carries `input_sha256` —
cite it when reporting a score so the result is reproducible.

Verify determinism any time: run twice on the same input and diff the bytes.

## Auth
None. The engine and spec are public; all computation is local.

## Operating Rules
1. Inputs must be real evidence with citable sources. Never fabricate
   evidence items to force a numeric score — that defeats the engine.
2. Report `insufficient-data` plainly. It is the honest cold-start outcome,
   not a failure.
3. When reporting a score, include the band, the context, and the
   `input_sha256`.
4. Do not edit `engine.py`'s weights, thresholds, or gates ad hoc — those
   are spec-versioned (spec §11). Propose changes as a spec bump instead.
