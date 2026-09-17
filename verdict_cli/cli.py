"""verdict — trust-scoring CLI for the CWI Verdict Engine.

Reads evidence JSON, scores it deterministically, and refuses honestly
(insufficient-data / evidence-disputed / unknown-context / invalid-input)
instead of inventing scores.
"""
import argparse
import json
import sys

from . import (__version__, example_input, explain, score_input,
               spec_text, engine_provenance)
from .report import write_reports


def _read_input(path):
    try:
        if path == "-":
            return json.load(sys.stdin), None
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, "input file not found: %s" % path
    except json.JSONDecodeError as exc:
        return None, "input is not valid JSON: %s" % exc
    except OSError as exc:
        return None, "could not read input: %s" % exc


def cmd_score(args):
    doc, err = _read_input(args.input)
    if err:
        print("verdict: %s" % err, file=sys.stderr)
        return 2
    out, code = score_input(doc)
    if args.out:
        jp, mp = write_reports(out, doc, args.out)
        print("  report.json: %s" % jp)
        print("  report.md:   %s" % mp)
        print("  status: %s" % out["status"])
        if out["status"] == "scored":
            print("  score: %s (%s)  input_sha256: %s" % (
                out["score"], out["band"], out["input_sha256"]))
    else:
        sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return code


def cmd_check(args):
    doc, err = _read_input(args.input)
    if err:
        print("verdict: %s" % err, file=sys.stderr)
        return 2
    out, code = score_input(doc)
    subj = (out.get("subject") or {}).get("agent_id", "?")
    if out["status"] == "scored":
        print("%s | %s | score %.3f (%s) | sha %s" % (
            subj, out["context"], out["score"], out["band"],
            (out["input_sha256"] or "")[:12]))
    else:
        missing = "; ".join(out.get("missing") or [])
        print("%s | %s | %s | %s" % (subj, out["context"], out["status"], missing))
    return code


def cmd_example(args):
    try:
        doc = example_input(args.kind)
    except ValueError as exc:
        print("verdict: %s" % exc, file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return 0


def cmd_spec(_args):
    sys.stdout.write(spec_text())
    return 0


def cmd_pin(_args):
    prov = engine_provenance()
    for k in ("engine_version", "spec_version", "source_repo",
              "source_branch", "source_path", "source_blob_sha", "pinned_on"):
        print("%s: %s" % (k, prov[k]))
    print("policy: vendored verbatim — never hand-edit; re-vendor on spec bump.")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="verdict",
        description="Deterministic, evidence-bound trust scoring for AI agents. "
                    "Never invents a score.")
    p.add_argument("--version", action="version", version="verdict-cli %s" % __version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="Score evidence JSON; write report.md + report.json.")
    s.add_argument("input", help="Evidence JSON file (or - for stdin).")
    s.add_argument("--out", metavar="DIR",
                   help="Write report.json + report.md into DIR (created if needed).")
    s.set_defaults(func=cmd_score)

    c = sub.add_parser("check", help="One-line verdict for pipelines.")
    c.add_argument("input", help="Evidence JSON file (or - for stdin).")
    c.set_defaults(func=cmd_check)

    e = sub.add_parser("example", help="Print a valid input template.")
    e.add_argument("--kind", default="insufficient",
                   choices=["insufficient", "disputed"],
                   help="Template flavor (default: insufficient). "
                        "There is no 'scored' template: scored examples would "
                        "need fabricated evidence.")
    e.set_defaults(func=cmd_example)

    sp = sub.add_parser("spec", help="Print the published scoring rules.")
    sp.set_defaults(func=cmd_spec)

    pn = sub.add_parser("pin", help="Show the vendored engine provenance.")
    pn.set_defaults(func=cmd_pin)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
