import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from judeoalgonquin.records import load_records


ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "schema" / "entry.schema.json"
ANCHOR_SCHEMA_PATH = ROOT / "schema" / "creative-anchor.schema.json"
ANCHOR_DATA = tuple(sorted((ROOT / "data" / "creative-anchors").glob("*.json")))
CONTACT_DATA = ROOT / "data" / "entries" / "n1-contact-lexicon.jsonl"
DATASETS = (
    ROOT / "tests" / "fixtures" / "creative_anchor_candidates.jsonl",
    ROOT / "data" / "entries" / "n1-pilot.jsonl",
    ROOT / "data" / "entries" / "n1-core-lexicon.jsonl",
    ROOT / "data" / "entries" / "n1-core-regressions.jsonl",
    ROOT / "data" / "entries" / "n1-contact-lexicon.jsonl",
    ROOT / "data" / "entries" / "n1-song-chorus.jsonl",
)


def public_record(record: dict) -> dict:
    return {key: value for key, value in record.items() if key != "_source"}


class JsonSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(
            cls.schema,
            format_checker=FormatChecker(),
        )
        cls.anchor_schema = json.loads(ANCHOR_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.anchor_schema)
        cls.anchor_validator = Draft202012Validator(
            cls.anchor_schema,
            format_checker=FormatChecker(),
        )

    def test_every_committed_record_satisfies_the_public_schema(self) -> None:
        for path in DATASETS:
            for record in load_records(path):
                with self.subTest(path=path.name, record=record["id"]):
                    self.validator.validate(public_record(record))

    def test_review_is_required_exactly_for_reviewed_lifecycle_states(self) -> None:
        candidate = public_record(load_records(DATASETS[0])[0])
        reviewed = copy.deepcopy(candidate)
        reviewed["status"] = "reviewed"
        with self.assertRaisesRegex(ValidationError, "review"):
            self.validator.validate(reviewed)

        candidate_with_review = copy.deepcopy(candidate)
        candidate_with_review["review"] = {
            "reviewer_type": "human",
            "reviewer_id": "owner",
            "authority": "project owner",
            "decision": "reviewed",
            "reviewed_at": "2026-07-12T00:00:00Z",
            "note": "Schema rejection fixture.",
        }
        with self.assertRaisesRegex(ValidationError, "should not be valid"):
            self.validator.validate(candidate_with_review)

    def test_contact_adapted_lexeme_requires_a_contact_language_layer(self) -> None:
        contact = public_record(load_records(CONTACT_DATA)[0])
        del contact["metadata"]["lexical_layer"]
        with self.assertRaisesRegex(ValidationError, "lexical_layer"):
            self.validator.validate(contact)

    def test_every_creative_anchor_ledger_satisfies_its_public_schema(self) -> None:
        for path in ANCHOR_DATA:
            with self.subTest(path=path.name):
                self.anchor_validator.validate(json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
