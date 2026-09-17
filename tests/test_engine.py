"""Tests for the vendored canonical engine: determinism, gates, damping,
refusals, bands. Fixtures here are SYNTHETIC — built only to verify the
math. They are test data, never presented as evidence."""
import copy
import hashlib
import json
import unittest
from pathlib import Path

from verdict_cli import _engine as E
from verdict_cli import score_input, example_input


# sha256 of verdict_cli/_engine.py as vendored 2026-09-17 (header banner
# included). If this fails, the scoring code was touched — re-vendor, never
# hand-edit.
ENGINE_FILE_SHA256 = "dcc525d8c8c363f96604c09d1e3ed719f77b46e2f6067bf6c4799cfe80392f04"


def ev(eid, issuer="issuer-a", cluster=None, itype="third_party",
       status="verified", wc=2):
    return {"evidence_id": eid, "kind": "test-kind", "issuer": issuer,
            "identity_cluster": cluster, "issuer_type": itype,
            "description": "synthetic test evidence", "status": status,
            "observed_at": "2026-09-17", "source_url": None,
            "source_ref": "test fixture", "weight_class": wc}


def doc(signals, context="agent-trust"):
    return {"engine_version": "1.0.0",
            "subject": {"agent_id": "TEST_SUBJECT", "display_name": "Test"},
            "context": context, "observed_at": "2026-09-17T00:00:00Z",
            "signals": signals}


def scored_doc():
    # gate: agent-trust needs 3 verified / 2 families / erc8004 required
    return doc({"erc8004": [ev("e1", issuer="i1"), ev("e2", issuer="i2")],
                "needle_drop": [ev("n1", issuer="i3", wc=3)],
                "first_spin": []})


class TestVendoredPin(unittest.TestCase):
    def test_engine_file_untouched(self):
        p = Path(__file__).resolve().parent.parent / "verdict_cli" / "_engine.py"
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(h, ENGINE_FILE_SHA256)
        self.assertEqual(E.ENGINE_VERSION, "1.0.0")
        self.assertEqual(E.SPEC_VERSION, "1.0.0")


class TestDeterminism(unittest.TestCase):
    def test_same_input_byte_identical(self):
        d = scored_doc()
        o1, c1 = score_input(copy.deepcopy(d))
        o2, c2 = score_input(copy.deepcopy(d))
        b1 = json.dumps(o1, indent=2, ensure_ascii=False)
        b2 = json.dumps(o2, indent=2, ensure_ascii=False)
        self.assertEqual(b1, b2)
        self.assertEqual(c1, c2)

    def test_input_sha256_recomputable(self):
        d = scored_doc()
        out, _ = score_input(d)
        blob = json.dumps(d, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8")
        self.assertEqual(out["input_sha256"], hashlib.sha256(blob).hexdigest())


class TestScoringMath(unittest.TestCase):
    def test_scored_status_and_value(self):
        # erc8004: kept_weight 4 -> 4/7 = 0.5714; needle_drop: 3 -> 3/6 = 0.5
        # mean = 0.5357 -> 0.536, band thin
        out, code = score_input(scored_doc())
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "scored")
        self.assertEqual(out["score"], 0.536)
        self.assertEqual(out["band"], "thin")
        self.assertEqual(out["missing"], [])

    def test_score_is_none_when_refused(self):
        out, _ = score_input(example_input("insufficient"))
        self.assertEqual(out["status"], "insufficient-data")
        self.assertIsNone(out["score"])
        self.assertIsNone(out["band"])

    def test_self_assertion_discount(self):
        d = doc({"erc8004": [ev("s1", issuer="me", itype="self", wc=2),
                             ev("t1", issuer="i1", wc=2),
                             ev("t2", issuer="i2", wc=2)],
                 "needle_drop": [ev("n1", issuer="i3", wc=2)],
                 "first_spin": []})
        out, _ = score_input(d)
        fam = out["families"]["erc8004"]
        # 2 + 2 + 1(self@0.5x) = 5 kept weight
        self.assertEqual(fam["kept_weight"], 5.0)
        self.assertEqual(fam["self_assertion_discounted"], ["s1"])

    def test_issuer_cap_damping(self):
        items = [ev("c1", issuer="a", cluster="one-human", wc=3),
                 ev("c2", issuer="b", cluster="one-human", wc=2),
                 ev("c3", issuer="c", cluster="one-human", wc=1)]
        d = doc({"erc8004": items,
                 "needle_drop": [ev("n1", issuer="i9", wc=2),
                                 ev("n2", issuer="i8", wc=2)],
                 "first_spin": []})
        out, code = score_input(d)
        self.assertEqual(code, 0)
        fam = out["families"]["erc8004"]
        self.assertEqual(fam["kept_evidence_ids"], ["c1", "c2"])
        self.assertEqual(len(fam["damped"]), 1)
        self.assertEqual(fam["damped"][0]["evidence_id"], "c3")
        self.assertEqual(fam["damped"][0]["reason"], "issuer-cap")

    def test_non_verified_counts_zero(self):
        d = doc({"erc8004": [ev("v1"), ev("cl", status="claimed"),
                             ev("pe", status="pending"), ev("re", status="refuted")],
                 "needle_drop": [ev("v2"), ev("v3")],
                 "first_spin": []})
        out, code = score_input(d)
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "scored")
        nc = out["families"]["erc8004"]["not_counted"]
        self.assertEqual(sorted(n["evidence_id"] for n in nc), ["cl", "pe", "re"])


class TestRefusals(unittest.TestCase):
    def test_insufficient_data_lists_missing(self):
        out, code = score_input(example_input("insufficient"))
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "insufficient-data")
        self.assertTrue(any("3 required" in m for m in out["missing"]))

    def test_disputed_refuses_whole_run(self):
        out, code = score_input(example_input("disputed"))
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "evidence-disputed")
        self.assertIsNone(out["score"])
        self.assertTrue(any("e8004-disputed-example" in m for m in out["missing"]))

    def test_unknown_context(self):
        out, code = score_input(doc({"erc8004": [], "needle_drop": [],
                                     "first_spin": []}, context="nope"))
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "unknown-context")
        self.assertIsNone(out["score"])

    def test_invalid_version(self):
        d = scored_doc()
        d["engine_version"] = "9.9.9"
        out, code = score_input(d)
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "invalid-input")
        self.assertIsNone(out["input_sha256"])

    def test_duplicate_evidence_id(self):
        d = doc({"erc8004": [ev("dup"), ev("dup")],
                 "needle_drop": [], "first_spin": []})
        out, code = score_input(d)
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "invalid-input")

    def test_missing_family_key(self):
        d = doc({"erc8004": [], "needle_drop": []})
        out, code = score_input(d)
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "invalid-input")

    def test_bad_weight_class(self):
        d = doc({"erc8004": [ev("w", wc=5)], "needle_drop": [],
                 "first_spin": []})
        out, code = score_input(d)
        self.assertEqual(code, 2)


class TestBands(unittest.TestCase):
    def test_band_boundaries(self):
        self.assertEqual(E._band_for(0.80), "established")
        self.assertEqual(E._band_for(0.799), "emerging")
        self.assertEqual(E._band_for(0.60), "emerging")
        self.assertEqual(E._band_for(0.40), "thin")
        self.assertEqual(E._band_for(0.20), "weak")
        self.assertEqual(E._band_for(0.199), "negligible")
        self.assertEqual(E._band_for(1.0), "established")


class TestContexts(unittest.TestCase):
    def test_music_review_gate(self):
        d = doc({"erc8004": [ev("a1"), ev("a2")], "needle_drop": [],
                 "first_spin": []}, context="music-review")
        out, _ = score_input(d)
        # 2 verified but none in first_spin/needle_drop -> insufficient
        self.assertEqual(out["status"], "insufficient-data")

    def test_payments_requires_both_families(self):
        d = doc({"erc8004": [ev("a1"), ev("a2")],
                 "needle_drop": [ev("n1")], "first_spin": []},
                context="payments")
        out, _ = score_input(d)
        self.assertEqual(out["status"], "scored")


if __name__ == "__main__":
    unittest.main()
