"""End-to-end CLI tests: every subcommand, exit codes, file outputs."""
import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import tempfile

from verdict_cli.cli import main as cli_main
from verdict_cli import example_input


def run_cli(argv, stdin_text=None):
    out, err = io.StringIO(), io.StringIO()
    if stdin_text is not None:
        fake_stdin = io.StringIO(stdin_text)
    else:
        fake_stdin = None
    import verdict_cli.cli as cli_mod
    old = cli_mod.sys.stdin
    try:
        if fake_stdin is not None:
            cli_mod.sys.stdin = fake_stdin
        with redirect_stdout(out), redirect_stderr(err):
            code = cli_main(argv)
    finally:
        cli_mod.sys.stdin = old
    return code, out.getvalue(), err.getvalue()


def write_input(d):
    td = tempfile.mkdtemp()
    p = Path(td) / "in.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return str(p)


class TestScoreCmd(unittest.TestCase):
    def test_score_stdout_json(self):
        from tests.test_engine import scored_doc
        code, so, _ = run_cli(["score", write_input(scored_doc())])
        self.assertEqual(code, 0)
        out = json.loads(so)
        self.assertEqual(out["status"], "scored")
        self.assertEqual(out["score"], 0.536)

    def test_score_out_writes_pair(self):
        from tests.test_engine import scored_doc
        with tempfile.TemporaryDirectory() as td:
            outdir = str(Path(td) / "run")
            code, so, _ = run_cli(["score", write_input(scored_doc()),
                                   "--out", outdir])
            self.assertEqual(code, 0)
            self.assertTrue((Path(outdir) / "report.json").is_file())
            self.assertTrue((Path(outdir) / "report.md").is_file())
            self.assertIn("report.json", so)
            self.assertIn("scored", so)

    def test_score_refusal_exit_zero(self):
        code, so, _ = run_cli(["score", write_input(
            example_input("insufficient"))])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(so)["status"], "insufficient-data")

    def test_score_invalid_input_exit_two(self):
        code, so, se = run_cli(["score", write_input({"nope": 1})])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(so)["status"], "invalid-input")

    def test_score_stdin_dash(self):
        from tests.test_engine import scored_doc
        blob = json.dumps(scored_doc())
        code, so, _ = run_cli(["score", "-"], stdin_text=blob)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(so)["status"], "scored")

    def test_score_missing_file(self):
        code, _, se = run_cli(["score", "/nonexistent/x.json"])
        self.assertEqual(code, 2)
        self.assertIn("not found", se)

    def test_score_malformed_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text("{not json", encoding="utf-8")
            code, _, se = run_cli(["score", str(p)])
            self.assertEqual(code, 2)
            self.assertIn("not valid JSON", se)


class TestCheckCmd(unittest.TestCase):
    def test_check_one_liner_scored(self):
        from tests.test_engine import scored_doc
        code, so, _ = run_cli(["check", write_input(scored_doc())])
        self.assertEqual(code, 0)
        self.assertIn("score 0.536 (thin)", so)
        self.assertIn("TEST_SUBJECT", so)

    def test_check_one_liner_refused(self):
        code, so, _ = run_cli(["check", write_input(
            example_input("disputed"))])
        self.assertEqual(code, 0)
        self.assertIn("evidence-disputed", so)


class TestExampleCmd(unittest.TestCase):
    def test_example_insufficient_valid(self):
        code, so, _ = run_cli(["example"])
        self.assertEqual(code, 0)
        d = json.loads(so)
        self.assertEqual(d["engine_version"], "1.0.0")
        self.assertEqual(sorted(d["signals"].keys()),
                         ["erc8004", "first_spin", "needle_drop"])

    def test_example_disputed(self):
        code, so, _ = run_cli(["example", "--kind", "disputed"])
        self.assertEqual(code, 0)
        d = json.loads(so)
        self.assertTrue(any(e["status"] == "disputed"
                            for e in d["signals"]["erc8004"]))

    def test_example_no_scored_kind(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli(["example", "--kind", "scored"])
        self.assertEqual(ctx.exception.code, 2)  # argparse rejects the choice


class TestSpecPinCmd(unittest.TestCase):
    def test_spec_prints_rules(self):
        code, so, _ = run_cli(["spec"])
        self.assertEqual(code, 0)
        for needle in ("Sybil", "insufficient-data", "agent-trust",
                       "0.80", "established"):
            self.assertIn(needle, so)

    def test_pin_prints_provenance(self):
        code, so, _ = run_cli(["pin"])
        self.assertEqual(code, 0)
        self.assertIn("e34b722e7efe86126c6ec1af0be99a8dd7a29953", so)
        self.assertIn("needs/verdict-engine", so)

    def test_version_flag(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli(["--version"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
