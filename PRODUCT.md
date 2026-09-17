# PRODUCT.md — Verdict CLI v1.0.0

## Purpose statement

Verdict CLI productizes CWI's trust-scoring primitive as real, sellable
software: any operator who needs to answer "should I trust this agent?"
feeds evidence JSON into a deterministic engine and gets back a verdict — a
score with a published band and a full evidence trace, or an honest refusal
when the evidence isn't there. It exists because agent ecosystems run on
trust claims, and most trust scores are vibes; this one is arithmetic with
receipts, and it says "I don't know" when it doesn't know.

## Real audience

- **AI-agent operators** deciding which agents to let into a workflow, a
  meeting room, or a deal — they need a reproducible trust check before
  granting access, not a gut feeling.
- **Marketplace / directory builders** (agent directories, skill stores,
  Moltbook-style networks) who need a deterministic, auditable scoring
  step they can run locally with zero dependencies.
- **CWI itself** — the Verdict Engine is the trust primitive underneath
  CWI's agent products (verdict-ledger #4 consumes it next); dogfooding it
  as a CLI hardens the primitive before anything depends on it.

## Result

A verdict — `report.json` (canonical engine output: status, score or null,
band, per-family evidence trace, `input_sha256`) + `report.md` (human
explanation: why this verdict, what was damped or not counted, exactly what
is missing, what to do next). Scores are citable: score + band + context +
`input_sha256` reproduces byte-identically.

## Mechanism

1. Operator assembles evidence JSON: subject, context (`agent-trust`,
   `music-review`, `payments`), `observed_at`, and three evidence families
   (`erc8004`, `needle_drop`, `first_spin`) with citable sources.
2. The vendored canonical engine (spec 1.0.0, pinned blob — never edited)
   admits only `verified` evidence, applies Sybil damping (issuer caps,
   identity clustering, self-assertion discount), checks the context gate,
   and scores or refuses.
3. CLI renders both reports; `check` gives pipelines a one-liner;
   `example` prints valid input templates; `spec` prints the published
   rules; `pin` shows the engine provenance for audit.
4. Determinism is structural: no clock, no randomness, no network — the
   test suite asserts byte-identical reruns.

## Verification

- 40-test suite (`python3 -m unittest discover -s tests`), all passing:
  vendored-file sha256 integrity pin, determinism (byte-identical reruns,
  recomputable `input_sha256`), scoring math (hand-computed fixtures),
  Sybil damping (issuer cap, identity clustering, self-discount),
  non-verified statuses counting zero, all four refusal statuses, band
  boundaries, all three context gates, CLI end-to-end (every subcommand,
  exit codes, stdin, malformed input, missing file), and report rendering
  (scored / refused / provenance anchored-unanchored).
- Stdlib only: zero dependencies, no network, no telemetry, no keys.
- Dogfood path: CWI's own agent evidence (MUSE_CWI Moltbook claim) is the
  `insufficient` example — the honest cold start, verified live.

## Kill rule

**Fewer than 5 external uses with receipts in 30 days → delist.**
"External" means a user outside CWI; "receipts" means a generated verdict
(report.md+json pair) the user can show. If operators aren't reaching for
a reproducible trust check, the primitive doesn't earn its shelf space —
cut it and keep the engine as an internal library.

## Price

**TBD — pending Black's approval. Do not publish a price.** No price is set,
shown, or implied anywhere in the product, docs, or reports. No payment
flow exists in v1.

## What v1 is NOT

- Not a trust oracle: it scores the evidence you give it. Fabricated
  evidence produces a fabricated-looking score with a real paper trail —
  the tool cannot stop you from lying to it, but the `input_sha256` means
  your lie is reproducible and attributable.
- Not a reputation system: no history, no decay, no cross-subject
  comparison. Snapshots only. (verdict-ledger, queue #4, is the scheduled
  re-check primitive.)
- Not a marketplace listing: no Gumroad product has been created, and none
  will be without Black's explicit approval.
- Not touching live CWI systems: this product reads evidence JSON you hand
  it. It does not query Moltbook, the ledger, or any chain.
