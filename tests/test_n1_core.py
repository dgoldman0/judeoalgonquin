import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from judeoalgonquin.evaluate import evaluate_pilot_compositions
from judeoalgonquin.orthography import assert_transport_round_trip
from judeoalgonquin.records import load_records, load_source_registry, validate_records
from judeoalgonquin.store import connect, index_records, search_text


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "entries"
LEXICON = DATA / "n1-core-lexicon.jsonl"
REGRESSIONS = DATA / "n1-core-regressions.jsonl"
HEBREW_SEEDS = ROOT / "data" / "research" / "n1-core-hebrew-seeds.json"
MUNSEE_SEEDS = ROOT / "data" / "research" / "n1-core-munsee-seeds.json"
SOURCES = ROOT / "references" / "sources.yaml"
QUERIES = ROOT / "tests" / "fixtures" / "n1_core_semantic_queries.json"
REPORT = ROOT / "docs" / "reports" / "n1-core-embedding-evaluation-2026-07-12.json"
POLICY = ROOT / "config" / "api-budget.json"


class N1CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        registry = load_source_registry(SOURCES)
        cls.records = validate_records(load_records(DATA), source_registry=registry)
        cls.by_id = {record["id"]: record for record in cls.records}
        cls.lexicon = validate_records(load_records(LEXICON), source_registry=registry)
        regression_ids = {
            record["id"] for record in load_records(REGRESSIONS)
        }
        cls.regressions = [
            record for record in cls.records if record["id"] in regression_ids
        ]

    def test_frozen_record_envelope(self) -> None:
        self.assertEqual(len(self.records), 92)
        self.assertEqual(len(self.lexicon), 60)
        self.assertEqual(len(self.regressions), 12)
        self.assertEqual(
            Counter(record["record_type"] for record in self.records),
            Counter(
                {
                    "lexeme": 64,
                    "morpheme": 8,
                    "construction": 5,
                    "phrase": 10,
                    "sentence": 5,
                }
            ),
        )
        self.assertEqual({record["status"] for record in self.records}, {"candidate"})

    def test_seed_packets_are_exactly_the_reviewed_25_plus_35(self) -> None:
        hebrew = json.loads(HEBREW_SEEDS.read_text(encoding="utf-8"))["records"]
        munsee = json.loads(MUNSEE_SEEDS.read_text(encoding="utf-8"))["records"]
        self.assertEqual(len(hebrew), 25)
        self.assertEqual(len(munsee), 35)
        self.assertEqual(len({item["id"] for item in [*hebrew, *munsee]}), 60)
        self.assertEqual(Counter(item["record_type"] for item in hebrew), {"lexeme": 24, "morpheme": 1})
        self.assertEqual(Counter(item["type"] for item in munsee), {"lexeme": 33, "morpheme": 2})

    def test_each_source_parent_has_independent_ordinary_life_coverage(self) -> None:
        hebrew = [
            record
            for record in self.lexicon
            if "hebrew-derived" in record["metadata"]["tags"]
        ]
        munsee = [
            record
            for record in self.lexicon
            if "munsee-derived" in record["metadata"]["tags"]
        ]
        self.assertEqual(len(hebrew), 25)
        self.assertEqual(len(munsee), 35)
        self.assertGreaterEqual(len({domain for record in hebrew for domain in record["metadata"]["domains"]}), 8)
        self.assertGreaterEqual(len({domain for record in munsee for domain in record["metadata"]["domains"]}), 8)

    def test_every_munsee_seed_round_trips_without_normalizing_away_source_symbols(self) -> None:
        packet = json.loads(MUNSEE_SEEDS.read_text(encoding="utf-8"))
        for seed in packet["records"]:
            with self.subTest(seed=seed["id"]):
                encoded = assert_transport_round_trip(seed["normalized_transport_input"])
                record_id = f"ja.{seed['type']}.munsee_{seed['id'].removeprefix('ja.seed.munsee.')}"
                record = self.by_id[record_id]
                self.assertEqual(
                    record["forms"]["judeo_algonquin"]["hebrew_script"], encoded
                )
                self.assertEqual(
                    record["forms"]["judeo_algonquin"]["orthography"]["source_exact"],
                    seed["source_form"],
                )

    def test_source_evidence_and_attribution_remain_bounded(self) -> None:
        for record in self.lexicon:
            evidence = record["source_evidence"][0]
            if "munsee-derived" in record["metadata"]["tags"]:
                self.assertEqual(len(record["source_evidence"]), 1)
                self.assertEqual(
                    evidence["source_id"], "omeara_delaware_stem_morphology_1990"
                )
                self.assertIn("no item-level speaker attribution", evidence["contributor_or_speaker"])
                self.assertEqual(evidence["license_status"], "copyrighted")
            else:
                self.assertEqual(
                    evidence["source_id"], "academy_hebrew_online_resources"
                )
                self.assertEqual(evidence["license_status"], "mixed_or_unknown")
                if record["id"] == "ja.lexeme.hebrew_mahar_tomorrow":
                    self.assertEqual(len(record["source_evidence"]), 2)
                    self.assertEqual(
                        record["source_evidence"][1]["source_id"], "bdb_1906_sefaria"
                    )
                else:
                    self.assertEqual(len(record["source_evidence"]), 1)

        cloth = self.by_id["ja.lexeme.munsee_wesapakwiiwan_cloth"]
        self.assertEqual(cloth["source_evidence"][0]["source_form"], "wšapakwiiwan")
        self.assertTrue(
            any("/wəšap-akwiiwan/" in value for value in cloth["grammatical_features"])
        )
        tomorrow = self.by_id["ja.lexeme.hebrew_mahar_tomorrow"]
        self.assertEqual(tomorrow["source_evidence"][0]["source_form"], "מחר")
        self.assertEqual(tomorrow["source_evidence"][1]["source_form"], "מָחָר")

    def test_every_new_alias_is_exactly_retrievable(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            connection = connect(Path(tempdir) / "n1-core.sqlite3")
            self.addCleanup(connection.close)
            index_records(connection, self.records)
            for record in self.lexicon:
                conlang = record["forms"]["judeo_algonquin"]
                aliases = [
                    *record["forms"]["english"],
                    conlang["hebrew_script"],
                    conlang["romanization"],
                ]
                for alias in aliases:
                    with self.subTest(record=record["id"], alias=alias):
                        results = search_text(connection, alias, limit=100)
                        exact_ids = {
                            result["id"]
                            for result in results
                            if result["lexical_score"] == 100.0
                        }
                        self.assertIn(record["id"], exact_ids)

    def test_all_compositions_pass_and_each_declared_rule_is_enforced(self) -> None:
        self.assertEqual(evaluate_pilot_compositions(self.records), [])
        for regression in self.regressions:
            changed = copy.deepcopy(self.records)
            target = next(record for record in changed if record["id"] == regression["id"])
            target["composition"]["construction_ids"] = []
            with self.subTest(regression=regression["id"]):
                self.assertTrue(
                    any(
                        regression["id"] in finding
                        and "construction declaration mismatch" in finding
                        for finding in evaluate_pilot_compositions(changed)
                    )
                )

    def test_renderers_reproduce_committed_jsonl_byte_for_byte(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        with tempfile.TemporaryDirectory() as tempdir:
            lexical_output = Path(tempdir) / "lexicon.jsonl"
            regression_output = Path(tempdir) / "regressions.jsonl"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "render_n1_core_lexicon.py"),
                    "--output",
                    str(lexical_output),
                ],
                cwd=ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "render_n1_core_regressions.py"),
                    "--output",
                    str(regression_output),
                ],
                cwd=ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(lexical_output.read_bytes(), LEXICON.read_bytes())
            self.assertEqual(regression_output.read_bytes(), REGRESSIONS.read_bytes())

    def test_embedding_report_matches_the_frozen_data_and_consumed_gate(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        aggregate = hashlib.sha256()
        hashes = {}
        for path in sorted(DATA.glob("*.jsonl")):
            content = path.read_bytes()
            hashes[path.name] = hashlib.sha256(content).hexdigest()
            aggregate.update(path.name.encode("utf-8"))
            aggregate.update(b"\0")
            aggregate.update(content)
            aggregate.update(b"\0")
        self.assertNotEqual(report["data_sha256"], aggregate.hexdigest())
        self.assertNotEqual(report["data_file_sha256"], hashes)
        correction = report["post_call_source_correction"]
        self.assertEqual(correction["current_data_sha256"], aggregate.hexdigest())
        self.assertEqual(correction["current_data_file_sha256"], hashes)
        self.assertEqual(correction["current_fresh_vectors"], 84)
        self.assertEqual(correction["current_stale_or_missing_vectors"], 8)
        self.assertFalse(correction["embedding_call_repeated"])
        self.assertEqual(
            report["query_fixture_sha256"], hashlib.sha256(QUERIES.read_bytes()).hexdigest()
        )
        self.assertEqual(report["prompt_tokens"], 50922)
        self.assertAlmostEqual(report["estimated_cost_usd"], 0.00101844)
        self.assertEqual(report["evaluation"]["recall_at_1"], 1.0)
        self.assertEqual(report["evaluation"]["recall_at_3"], 1.0)
        self.assertEqual(report["evaluation"]["mean_reciprocal_rank"], 1.0)
        self.assertTrue(report["evaluation"]["passed"])
        self.assertFalse(report["contains_vectors"])
        self.assertFalse(report["contains_credentials"])
        self.assertFalse(
            json.loads(POLICY.read_text(encoding="utf-8"))["paid_embeddings_enabled"]
        )


if __name__ == "__main__":
    unittest.main()
