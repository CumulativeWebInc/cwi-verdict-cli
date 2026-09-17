"""Tests for report.md rendering: scored, refused, provenance, honesty."""
import json
import unittest

from verdict_cli import score_input, example_input
from verdict_cli.report import render_report_md, write_reports
from tests.test_engine import scored_doc  # synthetic fixture


class TestReportMd(unittest.TestCase):
    def test_scored_report_has_score_band_trace(self):
        out, _ = score_input(scored_doc())
        md = render_report_md(out, scored_doc())
        self.assertIn("Verdict: SCORED", md)
        self.assertIn("0.536", md)
        self.assertIn("thin", md)
        self.assertIn("input_sha256", md)
        self.assertIn("| erc8004 |", md)
        self.assertIn("Honesty", md)

    def test_insufficient_report_lists_missing(self):
        d = example_input("insufficient")
        out, _ = score_input(d)
        md = render_report_md(out, d)
        self.assertIn("Verdict: INSUFFICIENT DATA", md)
        self.assertIn("never a number", md)
        self.assertIn("3 required", md)
        self.assertIn("honest cold start", md)

    def test_disputed_report_has_guidance(self):
        d = example_input("disputed")
        out, _ = score_input(d)
        md = render_report_md(out, d)
        self.assertIn("Verdict: EVIDENCE DISPUTED", md)
        self.assertIn("will not pick a side", md)

    def test_damped_items_visible(self):
        from tests.test_engine import ev, doc
        d = doc({"erc8004": [ev("c1", issuer="a", cluster="k", wc=3),
                             ev("c2", issuer="b", cluster="k", wc=2),
                             ev("c3", issuer="c", cluster="k", wc=1)],
                 "needle_drop": [ev("n1", wc=2), ev("n2", wc=2)],
                 "first_spin": []})
        out, _ = score_input(d)
        md = render_report_md(out, d)
        self.assertIn("c3", md)
        self.assertIn("issuer-cap", md)

    def test_provenance_unanchored_default(self):
        out, _ = score_input(scored_doc())
        md = render_report_md(out, scored_doc())
        self.assertIn("Provenance: **unanchored**", md)

    def test_provenance_anchored_with_ref(self):
        d = scored_doc()
        d["anchor_ref"] = "ots:calendar.example/2026-09-17/abc123"
        out, _ = score_input(d)
        md = render_report_md(out, d)
        self.assertIn("Provenance: **anchored**", md)
        self.assertIn("ots:calendar.example", md)

    def test_write_reports_creates_both_files(self):
        import tempfile
        from pathlib import Path
        d = scored_doc()
        out, _ = score_input(d)
        with tempfile.TemporaryDirectory() as td:
            jp, mp = write_reports(out, d, Path(td) / "run-1")
            self.assertTrue(Path(jp).is_file())
            self.assertTrue(Path(mp).is_file())
            back = json.loads(Path(jp).read_text(encoding="utf-8"))
            self.assertEqual(back["status"], "scored")
            self.assertEqual(back["score"], 0.536)


if __name__ == "__main__":
    unittest.main()
