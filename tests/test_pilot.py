import copy
import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from judeoalgonquin.evaluate import (
    evaluate_pilot_compositions,
    evaluate_semantic_rankings,
    load_semantic_queries,
)
from judeoalgonquin.records import load_records, load_source_registry, validate_records
from judeoalgonquin.store import connect, index_records, search_text


ROOT = Path(__file__).parents[1]
PILOT = ROOT / "data" / "entries" / "n1-pilot.jsonl"
SOURCES = ROOT / "references" / "sources.yaml"
SEMANTIC_QUERIES = ROOT / "tests" / "fixtures" / "n1_pilot_semantic_queries.json"
EMBEDDING_REPORT = ROOT / "docs" / "reports" / "n1-pilot-embedding-evaluation-2026-07-12.json"
BUDGET_POLICY = ROOT / "config" / "api-budget.json"


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = validate_records(
            load_records(PILOT), source_registry=load_source_registry(SOURCES)
        )
        cls.by_id = {record["id"]: record for record in cls.records}

    def test_bounded_record_mix_and_noncanonical_status(self) -> None:
        self.assertEqual(
            Counter(record["record_type"] for record in self.records),
            Counter(
                {
                    "lexeme": 7,
                    "morpheme": 5,
                    "construction": 5,
                    "phrase": 2,
                    "sentence": 1,
                }
            ),
        )
        self.assertEqual({record["status"] for record in self.records}, {"candidate"})
        self.assertEqual(
            Counter(record["revision"] for record in self.records),
            Counter({1: 8, 2: 12}),
        )
        self.assertTrue(
            all("noncanonical" in record["metadata"]["tags"] for record in self.records)
        )

    def test_every_declared_alias_is_exactly_retrievable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            connection = connect(Path(directory) / "pilot.sqlite3")
            self.addCleanup(connection.close)
            index_records(connection, self.records)
            for record in self.records:
                aliases = [
                    *record["forms"]["english"],
                    record["forms"]["judeo_algonquin"]["hebrew_script"],
                    record["forms"]["judeo_algonquin"]["romanization"],
                ]
                for alias in aliases:
                    with self.subTest(record=record["id"], alias=alias):
                        results = search_text(connection, alias, limit=100)
                        self.assertTrue(results)
                        direct_matches = {
                            result["id"]
                            for result in results
                            if result["lexical_score"] == 100.0
                        }
                        self.assertIn(record["id"], direct_matches)

    def test_direct_morpheme_alias_beats_source_form_mentions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            connection = connect(Path(directory) / "pilot.sqlite3")
            self.addCleanup(connection.close)
            index_records(connection, self.records)
            for alias, expected in (
                ("וְ־", "ja.morpheme.hebrew_coord_we"),
                ("הַ־", "ja.morpheme.hebrew_definite_ha"),
            ):
                with self.subTest(alias=alias):
                    self.assertEqual(search_text(connection, alias)[0]["id"], expected)

    def test_literal_and_idiomatic_translation_are_separate(self) -> None:
        for record in self.records:
            for item in record["senses"]:
                self.assertIn("literal", item["translations"])
                self.assertTrue(item["translations"]["idiomatic"])
        sentence = self.by_id["ja.sentence.n1_the_man_is_good"]
        translations = sentence["senses"][0]["translations"]
        self.assertEqual(translations["literal"], ["the-man he.is-good"])
        self.assertEqual(translations["idiomatic"], ["The man is good."])

    def test_exact_source_forms_and_attribution_caveats_are_preserved(self) -> None:
        expected_bdb = {
            "ja.lexeme.hebrew_bayit": "בַּ֫יִת",
            "ja.lexeme.hebrew_mayim": "מַי 1",
            "ja.lexeme.hebrew_lehem": "לֶ֫חֶם 1",
        }
        for record_id, expected_form in expected_bdb.items():
            evidence = next(
                item
                for item in self.by_id[record_id]["source_evidence"]
                if item["source_id"] == "bdb_1906_sefaria"
            )
            self.assertEqual(evidence["source_form"], expected_form)

        munsee_evidence = [
            evidence
            for record in self.records
            for evidence in record["source_evidence"]
            if evidence["source_id"] == "omeara_delaware_stem_morphology_1990"
        ]
        self.assertTrue(munsee_evidence)
        self.assertTrue(
            all(
                "no item-level speaker attribution" in evidence["contributor_or_speaker"]
                for evidence in munsee_evidence
            )
        )
        self.assertNotIn(
            "adult",
            self.by_id["ja.lexeme.munsee_lunew_man"]["senses"][0]["definition"],
        )
        pemsii = self.by_id["ja.lexeme.munsee_pemsii_walk"]
        self.assertIn("source verb class is unresolved", pemsii["senses"][0]["definition"])
        self.assertEqual(
            pemsii["source_evidence"][0]["source_form"],
            "/nə-pəmsii/ → mpəmsi",
        )

    def test_nominal_coordination_positive(self) -> None:
        self.assertEqual(evaluate_pilot_compositions(self.records), [])

    def test_nominal_coordination_negative(self) -> None:
        records = copy.deepcopy(self.records)
        phrase = next(record for record in records if record["id"] == "ja.phrase.n1_bread_and_water")
        phrase["composition"]["components"][1]["record_id"] = "ja.morpheme.hebrew_definite_ha"
        self.assertTrue(
            any("coordinator slot" in item for item in evaluate_pilot_compositions(records))
        )

    def test_definite_prefix_positive(self) -> None:
        self.assertEqual(evaluate_pilot_compositions(self.records), [])

    def test_definite_prefix_negative(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = next(record for record in records if record["id"] == "ja.sentence.n1_the_man_is_good")
        sentence["composition"]["components"][0]["record_id"] = "ja.lexeme.munsee_lunew_man"
        self.assertTrue(
            any("definite ha-" in item for item in evaluate_pilot_compositions(records))
        )

    def test_class_plural_positive(self) -> None:
        self.assertEqual(evaluate_pilot_compositions(self.records), [])

    def test_class_plural_negative(self) -> None:
        records = copy.deepcopy(self.records)
        phrase = next(record for record in records if record["id"] == "ja.phrase.n1_houses")
        phrase["composition"]["components"][1]["record_id"] = "ja.morpheme.munsee_plural_ak"
        self.assertTrue(
            any("conflicts with the host's pilot class" in item for item in evaluate_pilot_compositions(records))
        )

    def test_ai_third_positive(self) -> None:
        self.assertEqual(evaluate_pilot_compositions(self.records), [])

    def test_ai_third_negative(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = next(record for record in records if record["id"] == "ja.sentence.n1_the_man_is_good")
        sentence["composition"]["components"][3]["record_id"] = "ja.morpheme.munsee_plural_ak"
        self.assertTrue(
            any("followed by third-person -w" in item for item in evaluate_pilot_compositions(records))
        )

    def test_ai_third_checks_the_composed_sense_not_an_unrelated_sense(self) -> None:
        records = copy.deepcopy(self.records)
        predicate = next(
            record for record in records if record["id"] == "ja.lexeme.munsee_welesii_good"
        )
        selected = next(
            sense
            for sense in predicate["senses"]
            if sense["id"] == "ja.lexeme.munsee_welesii_good.sense.positive_quality"
        )
        selected["part_of_speech"] = "bound verb stem; source class unresolved"
        self.assertTrue(
            any(
                "followed by third-person -w" in item
                for item in evaluate_pilot_compositions(records)
            )
        )

    def test_contact_clause_positive(self) -> None:
        self.assertEqual(evaluate_pilot_compositions(self.records), [])

    def test_contact_clause_negative(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = next(record for record in records if record["id"] == "ja.sentence.n1_the_man_is_good")
        components = sentence["composition"]["components"]
        components[1]["role"], components[2]["role"] = components[2]["role"], components[1]["role"]
        self.assertTrue(
            any("subject before predicate" in item for item in evaluate_pilot_compositions(records))
        )

    def test_declared_construction_cannot_be_removed_to_bypass_checks(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = next(
            record for record in records if record["id"] == "ja.sentence.n1_the_man_is_good"
        )
        sentence["composition"]["construction_ids"].remove(
            "ja.construction.n1_definite_prefix"
        )
        self.assertTrue(
            any(
                "construction declaration mismatch" in item
                for item in evaluate_pilot_compositions(records)
            )
        )

    def test_surface_realization_and_host_class_are_checked(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = next(
            record for record in records if record["id"] == "ja.sentence.n1_the_man_is_good"
        )
        sentence["composition"]["components"][0]["realization"] = "not-ha"
        self.assertTrue(
            any("definite ha-" in item for item in evaluate_pilot_compositions(records))
        )

    def test_semantic_evaluation_metrics_are_deterministic(self) -> None:
        queries = load_semantic_queries(SEMANTIC_QUERIES)
        record_ids = [query["expected_id"] for query in queries]
        record_vectors = [
            [1.0 if column == row else 0.0 for column in range(len(queries))]
            for row in range(len(queries))
        ]
        result = evaluate_semantic_rankings(
            record_ids,
            record_vectors,
            queries,
            record_vectors,
        )
        self.assertEqual(result["query_count"], 5)
        self.assertEqual(result["recall_at_1"], 1.0)
        self.assertEqual(result["recall_at_3"], 1.0)
        self.assertEqual(result["mean_reciprocal_rank"], 1.0)

    def test_live_report_preserves_pre_correction_result_and_consumed_gate(self) -> None:
        report = json.loads(EMBEDDING_REPORT.read_text(encoding="utf-8"))
        current_hash = hashlib.sha256(PILOT.read_bytes()).hexdigest()
        self.assertNotEqual(report["data_sha256"], current_hash)
        self.assertEqual(
            report["post_call_source_correction"]["current_data_sha256"],
            current_hash,
        )
        self.assertEqual(report["successful_requests"], 1)
        self.assertEqual(report["failed_or_unknown_attempts"], 1)
        self.assertEqual(report["conservative_cumulative_accounted_input_tokens"], 58102)
        self.assertEqual(
            report["post_call_source_correction"]["current_stale_or_missing_vectors"],
            12,
        )
        self.assertFalse(report["contains_vectors"])
        self.assertFalse(report["contains_credentials"])
        policy = json.loads(BUDGET_POLICY.read_text(encoding="utf-8"))
        self.assertFalse(policy["paid_embeddings_enabled"])


if __name__ == "__main__":
    unittest.main()
