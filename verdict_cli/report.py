"""Human-readable verdict reports. The machine-readable artifact is the
canonical engine output (report.json); this module renders report.md —
an explanation of *why* the verdict is what it is."""
import json
from pathlib import Path

BAND_MEANINGS = {
    "established": "Deep, multi-family verified evidence.",
    "emerging": "Solid evidence, still building.",
    "thin": "Real evidence, but sparse.",
    "weak": "Minimal verified signal.",
    "negligible": "Barely above cold start.",
}

REFUSAL_GUIDANCE = {
    "insufficient-data": (
        "This is the honest cold start, not a failure. The `missing` list "
        "above says exactly what evidence would change this verdict. Add "
        "verified evidence with citable sources and re-run — never fabricate "
        "evidence to force a number."),
    "evidence-disputed": (
        "A live dispute is resolved off-engine; this tool will not pick a "
        "side. Resolve or remove the disputed items, then re-run."),
    "unknown-context": (
        "Use one of the registered contexts: agent-trust, music-review, "
        "payments. Trust is not fungible across use cases."),
    "invalid-input": (
        "The input failed schema validation. Fix the listed errors and "
        "re-run. Exit code 2."),
}


def _provenance(doc):
    ref = doc.get("anchor_ref") if isinstance(doc, dict) else None
    if isinstance(ref, str) and ref.strip():
        return "anchored", ref.strip()
    return "unanchored", None


def render_report_md(out, doc):
    """Render the human-readable report for an engine output dict."""
    subj = out.get("subject") or {}
    name = subj.get("display_name") or subj.get("agent_id") or "unknown subject"
    agent_id = subj.get("agent_id") or "—"
    status = out.get("status")
    prov, anchor_ref = _provenance(doc)

    L = []
    L.append("# Verdict Report — %s" % name)
    L.append("")
    L.append("Subject `%s` · context `%s` · observed `%s`" % (
        agent_id, out.get("context"), out.get("observed_at")))
    L.append("Engine `%s` %s / spec `%s` · input_sha256 `%s`" % (
        out.get("engine"), out.get("engine_version"),
        out.get("spec_version"), out.get("input_sha256")))
    L.append("Provenance: **%s**%s" % (
        prov, (" (`%s`)" % anchor_ref) if anchor_ref else
        " — verdict verified on a snapshot; source stability not pinned"))
    L.append("")
    L.append("## Verdict: %s" % status.upper().replace("-", " "))
    L.append("")

    if status == "scored":
        L.append("- **Score:** `%s`" % out["score"])
        L.append("- **Band:** `%s` — %s" % (
            out["band"], BAND_MEANINGS.get(out["band"], "")))
        L.append("- Cite as: score %s (%s), context %s, input_sha256 `%s`" % (
            out["score"], out["band"], out["context"], out["input_sha256"]))
        L.append("")
        L.append("### Evidence trace (per family)")
        L.append("")
        L.append("| family | submitted | verified | kept | kept_weight | family_score |")
        L.append("|---|---|---|---|---|---|")
        for fam, f in (out.get("families") or {}).items():
            L.append("| %s | %d | %d | %d | %.3f | %.3f |" % (
                fam, f["evidence_submitted"], f["verified_count"],
                f["kept_count"], f["kept_weight"], f["family_score"]))
        L.append("")
        damped_any = False
        for fam, f in (out.get("families") or {}).items():
            for d in f.get("damped", []):
                if not damped_any:
                    L.append("### Damped (Sybil control — visible, not counted)")
                    L.append("")
                    damped_any = True
                L.append("- `%s` (%s): %s — %s" % (
                    d["evidence_id"], fam, d["reason"], d["detail"]))
        if damped_any:
            L.append("")
        nc_any = False
        for fam, f in (out.get("families") or {}).items():
            for n in f.get("not_counted", []):
                if not nc_any:
                    L.append("### Not counted (status is not verified)")
                    L.append("")
                    nc_any = True
                L.append("- `%s` (%s): status `%s` — %s" % (
                    n["evidence_id"], fam, n["status"], n["reason"]))
        if nc_any:
            L.append("")
        gate = out.get("gate") or {}
        if gate:
            L.append("Gate: %d verified across %d families "
                     "(required: %d verified, %d families) — %s" % (
                         gate["verified_found"],
                         len(gate["families_with_verified"]),
                         gate["min_verified"], gate["min_families"],
                         "MET" if gate["met"] else "NOT MET"))
            L.append("")
    else:
        L.append("No score was produced. A null score is never a number.")
        L.append("")
        missing = out.get("missing") or []
        if missing:
            L.append("### What is missing / wrong")
            L.append("")
            for m in missing:
                L.append("- %s" % m)
            L.append("")
        guide = REFUSAL_GUIDANCE.get(status)
        if guide:
            L.append(guide)
            L.append("")

    notes = out.get("notes") or {}
    if notes:
        L.append("### Evidence notes")
        L.append("")
        for k, v in notes.items():
            L.append("- **%s:** %s" % (k, v))
        L.append("")

    L.append("---")
    L.append("### Honesty")
    L.append("")
    L.append("- This report structures evidence; it does not create trust. "
             "A score traces only to the evidence cited above.")
    L.append("- `insufficient-data` is the correct answer for new subjects. "
             "Never present it as a failure, and never fabricate evidence "
             "to force a number.")
    L.append("- Bands describe evidence depth, not character. Re-run with "
             "fresh `observed_at` as evidence changes; scores are snapshots.")
    L.append("")
    return "\n".join(L)


def write_reports(out, doc, outdir):
    """Write report.json (canonical engine output) + report.md (explanation).

    Returns (json_path, md_path). Creates outdir if needed.
    """
    d = Path(outdir)
    d.mkdir(parents=True, exist_ok=True)
    jp = d / "report.json"
    mp = d / "report.md"
    jp.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    mp.write_text(render_report_md(out, doc), encoding="utf-8")
    return str(jp), str(mp)
