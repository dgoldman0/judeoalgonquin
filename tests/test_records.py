import copy
import json
import unittest
from pathlib import Path

from judeoalgonquin.records import (
    LEVELS,
    RECORD_TYPES,
    STATUSES,
    TOP_LEVEL_REQUIRED,
    ValidationError,
    load_records,
    load_source_registry,
    load_source_registry_ids,
    validate_records,
)


FIXTURE = Path(__file__).parent / "fixtures" / "creative_anchor_candidates.jsonl"
PILOT = Path(__file__).parents[1] / "data" / "entries" / "n1-pilot.jsonl"
SOURCES = Path(__file__).parents[1] / "references" / "sources.yaml"


class RecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = validate_records(load_records(FIXTURE))

    def test_fixture_is_valid_and_noncanonical(self) -> None:
        self.assertEqual(len(self.records), 3)
        self.assertEqual({record["status"] for record in self.records}, {"candidate"})
        self.assertTrue(
            all("unverified" in record["metadata"]["tags"] for record in self.records)
        )

    def test_duplicate_id_fails(self) -> None:
        duplicate = copy.deepcopy(self.records[0])
        with self.assertRaisesRegex(ValidationError, "duplicate"):
            validate_records([*copy.deepcopy(self.records), duplicate])

    def test_unknown_dependency_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["relations"]["depends_on"] = ["ja.lexeme.does_not_exist"]
        with self.assertRaisesRegex(ValidationError, "unknown ID"):
            validate_records(records)

    def test_all_lifecycle_reviews_require_a_human(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["status"] = "reviewed"
        records[0]["review"] = {
            "reviewer_type": "model",
            "reviewer_id": "test-reviewer",
            "authority": "unit test",
            "decision": "reviewed",
            "reviewed_at": "2026-07-12T00:00:00Z",
            "note": "invalid automated promotion",
        }
        with self.assertRaisesRegex(ValidationError, "must be human"):
            validate_records(records)

    def test_timestamps_require_timezone_and_fail_cleanly(self) -> None:
        for bad_timestamp in ("2026-07-12", "2026-07-12T00:00:00"):
            with self.subTest(timestamp=bad_timestamp):
                records = copy.deepcopy(self.records)
                records[0]["created_at"] = bad_timestamp
                records[0]["updated_at"] = "2026-07-12T00:00:00Z"
                with self.assertRaisesRegex(ValidationError, "with timezone required"):
                    validate_records(records)

    def test_source_evidence_carries_policy_fields(self) -> None:
        schema = json.loads(
            (Path(__file__).parents[1] / "schema" / "entry.schema.json").read_text(
                encoding="utf-8"
            )
        )
        required = set(schema["properties"]["source_evidence"]["items"]["required"])
        self.assertTrue(
            {
                "grammatical_information",
                "contributor_or_speaker",
                "confidence",
                "uncertainty",
            }.issubset(required)
        )

        records = copy.deepcopy(self.records)
        records[0]["source_evidence"] = [
            {
                "source_id": "not_checked_without_a_registry",
                "language": "Test language",
                "lect": "",
                "source_form": "form",
                "source_meaning": "meaning",
                "grammatical_information": "noun",
                "locator": "entry form",
                "contributor_or_speaker": "",
                "license_status": "citation only",
                "accessed_at": "2026-07-12",
                "confidence": "certain-ish",
                "uncertainty": "Speaker attribution not published.",
            }
        ]
        with self.assertRaisesRegex(ValidationError, "invalid confidence"):
            validate_records(records)

    def test_historical_claim_requires_locator_and_source(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["formation"]["historical_etymology"] = [
            {"claim": "unsupported", "source_ids": [], "locator": "", "confidence": "low"}
        ]
        with self.assertRaises(ValidationError):
            validate_records(records)

    def test_bidi_control_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["notes"]["design"].append("unsafe\u202econtrol")
        with self.assertRaisesRegex(ValidationError, "unsafe code points"):
            validate_records(records)

    def test_malformed_status_is_controlled_validation_error(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["status"] = []
        with self.assertRaisesRegex(ValidationError, "invalid status"):
            validate_records(records)

    def test_unknown_nested_field_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["metadata"]["invented_field"] = True
        with self.assertRaisesRegex(ValidationError, "unknown fields"):
            validate_records(records)

    def test_source_ids_are_checked_against_registry(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["provenance"]["source_ids"] = ["not_a_real_source"]
        source_ids = load_source_registry_ids(Path(__file__).parents[1] / "references" / "sources.yaml")
        with self.assertRaisesRegex(ValidationError, "unknown source registry ID"):
            validate_records(records, source_registry_ids=source_ids)

    def test_registry_forbids_lexical_use_of_context_only_source(self) -> None:
        records = copy.deepcopy(self.records)
        sense_id = records[0]["senses"][0]["id"]
        records[0]["formation"]["inputs"] = [
            {
                "input_type": "source_record",
                "input_id": "munsee_delaware_nation_about",
                "form": "test",
                "contribution": "Invalid attempt to treat a context page as a dictionary.",
            }
        ]
        records[0]["source_evidence"] = [
            {
                "source_id": "munsee_delaware_nation_about",
                "language": "Munsee",
                "lect": "Lunaape",
                "source_form": "test",
                "source_meaning": "test",
                "grammatical_information": "noun",
                "locator": "About page",
                "contributor_or_speaker": "",
                "license_status": "unknown",
                "accessed_at": "2026-07-12",
                "confidence": "high",
                "uncertainty": "The page is not a lexical source.",
                "supports_sense_ids": [sense_id],
                "use_type": "lexical",
                "gap_reason": None,
            }
        ]
        records[0]["provenance"]["source_ids"] = ["munsee_delaware_nation_about"]
        registry = load_source_registry(Path(__file__).parents[1] / "references" / "sources.yaml")
        with self.assertRaisesRegex(ValidationError, "registry forbids"):
            validate_records(records, source_registry=registry)

    def test_canonical_legacy_or_unverified_record_is_rejected(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["status"] = "canonical"
        records[0]["review"] = {
            "reviewer_type": "human",
            "reviewer_id": "owner",
            "authority": "project owner",
            "decision": "canonical",
            "reviewed_at": "2026-07-12T00:00:00Z",
            "note": "This must still fail the provenance gate.",
        }
        with self.assertRaisesRegex(ValidationError, "legacy imports cannot be canonical"):
            validate_records(records)

    def test_canon_blocking_tags_and_unresolved_source_gaps_are_enforced(self) -> None:
        registry = load_source_registry(SOURCES)
        pilot = validate_records(load_records(PILOT), source_registry=registry)

        tagged = copy.deepcopy(pilot)
        tagged[0]["status"] = "canonical"
        tagged[0]["review"] = {
            "reviewer_type": "human",
            "reviewer_id": "owner",
            "authority": "project owner",
            "decision": "canonical",
            "reviewed_at": "2026-07-12T00:00:00Z",
            "note": "Negative gate fixture.",
        }
        with self.assertRaisesRegex(ValidationError, "canon-blocking tags remain"):
            validate_records(tagged, source_registry=registry)

        gap_blocked = copy.deepcopy(pilot)
        munsee = next(
            record for record in gap_blocked if record["id"] == "ja.lexeme.munsee_lunew_man"
        )
        munsee["status"] = "canonical"
        munsee["metadata"]["tags"] = [
            tag
            for tag in munsee["metadata"]["tags"]
            if tag not in {"candidate", "noncanonical", "provisional-orthography"}
        ]
        munsee["review"] = {
            "reviewer_type": "human",
            "reviewer_id": "owner",
            "authority": "project owner",
            "decision": "canonical",
            "reviewed_at": "2026-07-12T00:00:00Z",
            "note": "Negative source-gap fixture.",
        }
        with self.assertRaisesRegex(
            ValidationError, "munsee_current_community_lexical_guidance"
        ):
            validate_records(gap_blocked, source_registry=registry)

    def test_composed_records_require_a_literal_translation(self) -> None:
        registry = load_source_registry(SOURCES)
        pilot = validate_records(load_records(PILOT), source_registry=registry)
        phrase = next(record for record in pilot if record["record_type"] == "phrase")
        phrase["senses"][0]["translations"]["literal"] = []
        with self.assertRaisesRegex(ValidationError, "at least 1 value"):
            validate_records(pilot, source_registry=registry)

    def test_dependency_revision_mismatch_and_cycle_fail(self) -> None:
        stale = copy.deepcopy(self.records)
        stale[0]["revision"] += 1
        with self.assertRaisesRegex(ValidationError, "stale revision"):
            validate_records(stale)

        cyclic = copy.deepcopy(self.records)
        cyclic[0]["relations"]["depends_on"] = [cyclic[1]["id"]]
        cyclic[0]["relations"]["dependency_revisions"] = {
            cyclic[1]["id"]: cyclic[1]["revision"]
        }
        with self.assertRaisesRegex(ValidationError, "dependency cycle"):
            validate_records(cyclic)

    def test_schema_carries_composition_paradigm_and_review_contracts(self) -> None:
        schema = json.loads(
            (Path(__file__).parents[1] / "schema" / "entry.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("translations", schema["properties"]["senses"]["items"]["properties"])
        self.assertIn("composition", schema["properties"])
        self.assertIn("construction_spec", schema["properties"])
        self.assertIn("paradigm", schema["properties"])
        self.assertIn("reviewer_id", schema["properties"]["review"]["required"])
        self.assertTrue(schema["allOf"])

    def test_runtime_enums_and_required_fields_match_schema(self) -> None:
        schema = json.loads(
            (Path(__file__).parents[1] / "schema" / "entry.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(set(schema["required"]), TOP_LEVEL_REQUIRED)
        self.assertEqual(set(schema["properties"]["record_type"]["enum"]), RECORD_TYPES)
        self.assertEqual(set(schema["properties"]["status"]["enum"]), STATUSES)
        self.assertEqual(set(schema["properties"]["level"]["enum"]), LEVELS)

    def test_narrative_clause_and_participant_ledger_is_representable(self) -> None:
        construction = copy.deepcopy(self.records[0])
        construction["id"] = "ja.construction.test_foreground_chain"
        construction["record_type"] = "construction"
        construction["senses"][0]["id"] = (
            "ja.construction.test_foreground_chain.sense.foreground"
        )
        construction["construction_spec"] = {
            "kind": "discourse",
            "function": "Test foreground chaining.",
            "formalism": "Clause A then clause B.",
            "host_classes": ["clause"],
            "ordering": ["foreground clauses occur in narrative order"],
            "allomorphy": [],
            "restrictions": ["test-only construction"],
            "counterexamples": ["a background clause does not advance the chain"],
            "test_refs": [
                "tests.test_records.narrative_clause_positive",
                "tests.test_records.narrative_clause_negative",
            ],
            "productivity": "productive_candidate",
        }

        sentence = copy.deepcopy(self.records[1])
        sentence["id"] = "ja.sentence.test_narrative"
        sentence["record_type"] = "sentence"
        sentence["senses"][0]["id"] = "ja.sentence.test_narrative.sense.event"
        sentence["relations"]["depends_on"] = [
            "ja.lexeme.legacy_home",
            construction["id"],
        ]
        sentence["relations"]["dependency_revisions"] = {
            "ja.lexeme.legacy_home": self.records[0]["revision"],
            construction["id"]: construction["revision"],
        }
        sentence["composition"]["construction_ids"] = [construction["id"]]
        sentence["narrative_analysis"] = {
            "clauses": [
                {
                    "clause_id": "c1",
                    "construction_ids": [construction["id"]],
                    "event_role": "foreground",
                    "participants": [
                        {"participant_id": "p1", "discourse_status": "proximate"},
                        {"participant_id": "p2", "discourse_status": "obviative"},
                    ],
                    "center_shift": False,
                }
            ],
            "transition": None,
        }
        records = [*copy.deepcopy(self.records), construction, sentence]
        self.assertEqual(len(validate_records(records)), 5)


if __name__ == "__main__":
    unittest.main()
