"""verdict-cli — standalone trust-scoring CLI for the CWI Verdict Engine.

Public API:
    score_input(doc)      -> (output_dict, exit_code)  canonical engine run
    explain(doc)          -> str                       human-readable verdict
    spec_text()           -> str                       published scoring rules
    example_input(kind)   -> dict                      valid input templates
    engine_provenance()   -> dict                      vendored engine pin
    __version__
"""
from . import _engine as _engine  # noqa: F401  (vendored, do not touch)
from .report import write_reports, render_report_md  # noqa: F401

__version__ = "1.0.0"

ENGINE_PIN = {
    "engine_version": _engine.ENGINE_VERSION,
    "spec_version": _engine.SPEC_VERSION,
    "source_repo": "CumulativeWebInc/cwi-learn",
    "source_branch": "needs/verdict-engine",
    "source_path": "trust/engine.py",
    "source_blob_sha": "e34b722e7efe86126c6ec1af0be99a8dd7a29953",
    "pinned_on": "2026-09-17",
}


def score_input(doc):
    """Run the canonical engine on a parsed input dict.

    Returns (output_dict, exit_code). 0 = scored or clean refusal
    (insufficient-data, evidence-disputed, unknown-context);
    2 = invalid-input (refusal JSON still returned).
    Never invents a score: insufficient or disputed evidence yields a
    refusal status, never a number.
    """
    return _engine.run(doc)


def engine_provenance():
    """Where the vendored scoring code came from. Audit me."""
    return dict(ENGINE_PIN)


def _example_base(kind):
    # Real, citable CWI evidence only — the spec's own MUSE_CWI example.
    # The Needle Drop ledger is honestly empty; First Spin has no published
    # verdicts on file. So the honest example outcome is insufficient-data,
    # and the CLI says so instead of fabricating a scored example.
    doc = {
        "engine_version": "1.0.0",
        "subject": {"agent_id": "MUSE_CWI",
                    "display_name": "KingCode (CWI chief agent)"},
        "context": "agent-trust",
        "observed_at": "2026-09-17T00:00:00Z",
        "signals": {
            "erc8004": [
                {"evidence_id": "e8004-moltbook-claim-20260915",
                 "kind": "protocol-registration-claim",
                 "issuer": "moltbook",
                 "identity_cluster": None,
                 "issuer_type": "third_party",
                 "description": ("MUSE_CWI (KingCode) Moltbook account claimed "
                                 "— email verified."),
                 "status": "verified",
                 "observed_at": "2026-09-15",
                 "source_url": None,
                 "source_ref": "CWI agent watchlist + Moltbook heartbeat logs, 2026-09-15",
                 "weight_class": 2}
            ],
            "needle_drop": [],
            "first_spin": [],
        },
        "evidence_notes": {
            "needle_drop": "Ledger verified empty as of 2026-09-17 (ships empty by design).",
            "first_spin": "No published First Spin verdicts on file; worked examples excluded per spec.",
        },
    }
    if kind == "disputed":
        doc["signals"]["erc8004"].append(
            {"evidence_id": "e8004-disputed-example",
             "kind": "protocol-registration-claim",
             "issuer": "example-issuer",
             "identity_cluster": None,
             "issuer_type": "third_party",
             "description": "Illustrative disputed item — delete before real use.",
             "status": "disputed",
             "observed_at": "2026-09-17",
             "source_url": None,
             "source_ref": "template only",
             "weight_class": 2}
        )
    return doc


def example_input(kind="insufficient"):
    """A valid input template. kinds: 'insufficient' (default), 'disputed'.

    There is deliberately no 'scored' template: a scored example would need
    fabricated evidence, and this tool never fabricates evidence.
    """
    if kind not in ("insufficient", "disputed"):
        raise ValueError("kind must be 'insufficient' or 'disputed'")
    return _example_base(kind)


def spec_text():
    """The published scoring rules, as plain text. No hidden weights."""
    e = _engine
    lines = [
        "CWI Verdict Engine — scoring rules (spec %s, engine %s)" % (
            e.SPEC_VERSION, e.ENGINE_VERSION),
        "",
        "Evidence admission: only status 'verified' counts toward a score.",
        "  claimed / pending / refuted -> weight 0 (listed, not counted).",
        "  disputed -> the whole run is REFUSED (evidence-disputed).",
        "",
        "Weight classes (public):",
        "  1 = self-asserted (subject vouches for itself)",
        "  2 = third-party attested (independent platform/observer)",
        "  3 = protocol- or ledger-sealed (hash-chained / on-chain)",
        "",
        "Sybil damping (deterministic, all damped items stay visible):",
        "  D1 issuer cap: one identity cluster keeps at most %d verified items" % e.ISSUER_CAP_PER_FAMILY,
        "      per family (highest weight class first, ties by evidence_id).",
        "  D2 identity clustering: issuers sharing an identity_cluster count as one.",
        "  D3 self-assertion discount: issuer_type 'self' counts at %.1f x weight." % e.SELF_ASSERTION_FACTOR,
        "",
        "Family score: kept_weight / (kept_weight + %.1f)  (saturation constant)" % e.SATURATION_K,
        "Final score: mean of family scores over families with >=1 kept item,",
        "  rounded to 3 decimals. Bands:",
    ]
    for threshold, band in e.BANDS:
        lines.append("  >= %.2f  %s" % (threshold, band))
    lines += [
        "",
        "Context gates (checked on PRE-damping verified counts):",
    ]
    for name, cfg in e.CONTEXTS.items():
        req = ", ".join(cfg["required_families"]) or "—"
        anyof = ", ".join(cfg["required_any_of"]) or "—"
        lines.append("  %s: min_verified=%d, min_families=%d, required=[%s], any_of=[%s]"
                     % (name, cfg["min_verified"], cfg["min_families"], req, anyof))
        lines.append("      %s" % cfg["rationale"])
    lines += [
        "",
        "Refusals (never a number):",
        "  insufficient-data  — context gate not met (the honest cold start).",
        "  evidence-disputed  — any submitted evidence is disputed.",
        "  unknown-context    — context not in the registry above.",
        "  invalid-input      — schema violation (exit code 2).",
        "",
        "Determinism: no clock reads, no randomness, no network. Same input",
        "  -> byte-identical output. Every output carries input_sha256.",
        "Provenance: scored verdicts are 'unanchored' unless the input carries",
        "  an anchor_ref (content pinned at scoring time) -> 'anchored'.",
    ]
    return "\n".join(lines) + "\n"


def explain(doc):
    """One human-readable verdict summary for a parsed input dict."""
    out, _ = score_input(doc)
    return render_report_md(out, doc)
