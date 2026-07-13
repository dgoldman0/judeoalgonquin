import copy
import unittest
from pathlib import Path

from judeoalgonquin.anchors import load_anchor_ledgers, validate_anchor_ledgers
from judeoalgonquin.records import (
    ValidationError,
    load_records,
    load_source_registry,
    validate_records,
)


ROOT = Path(__file__).parents[1]
ANCHORS = ROOT / "data" / "creative-anchors"
DATA = ROOT / "data" / "entries"
SOURCES = ROOT / "references" / "sources.yaml"


class CreativeAnchorLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = validate_records(
            load_records(DATA),
            source_registry=load_source_registry(SOURCES),
        )
        cls.ledgers = validate_anchor_ledgers(
            load_anchor_ledgers(ANCHORS), cls.records
        )
        cls.by_id = {ledger["anchor_id"]: ledger for ledger in cls.ledgers}

    def test_line_complete_ledgers_validate(self) -> None:
        self.assertEqual(set(self.by_id), {
            "anchor.we_walk_well",
            "anchor.when_the_lights_learn_our_names",
        })
        self.assertEqual(sum(len(item["segments"]) for item in self.ledgers), 41)
        self.assertEqual(sum(len(item["requirements"]) for item in self.ledgers), 16)
        self.assertEqual(len(self.by_id["anchor.we_walk_well"]["segments"]), 28)
        self.assertEqual(
            len(self.by_id["anchor.when_the_lights_learn_our_names"]["segments"]),
            13,
        )

    def test_record_links_are_revision_and_sense_pinned(self) -> None:
        ledgers = copy.deepcopy(self.ledgers)
        link = ledgers[0]["requirements"][0]["current_record_links"][0]
        link["record_revision"] += 1
        with self.assertRaisesRegex(ValidationError, "stale revision"):
            validate_anchor_ledgers(ledgers, self.records)

        ledgers = copy.deepcopy(self.ledgers)
        link = ledgers[0]["requirements"][0]["current_record_links"][0]
        link["sense_id"] = "ja.lexeme.contact_person.sense.not_owned"
        with self.assertRaisesRegex(ValidationError, "not owned"):
            validate_anchor_ledgers(ledgers, self.records)

    def test_donor_only_cannot_masquerade_as_contact_coverage(self) -> None:
        ledgers = copy.deepcopy(self.ledgers)
        donor_link = next(
            link
            for ledger in ledgers
            for requirement in ledger["requirements"]
            for link in requirement["current_record_links"]
            if link["relationship"] == "donor_lead"
        )
        donor_link["relationship"] = "contact_candidate"
        donor_link["coverage"] = "contact_candidate"
        with self.assertRaisesRegex(ValidationError, "not a contact-language candidate"):
            validate_anchor_ledgers(ledgers, self.records)

    def test_source_hash_and_repeat_links_are_enforced(self) -> None:
        ledgers = copy.deepcopy(self.ledgers)
        ledgers[0]["source_block"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "expected current block"):
            validate_anchor_ledgers(ledgers, self.records)

        we_walk = self.by_id["anchor.we_walk_well"]
        final_chorus = [
            segment for segment in we_walk["segments"] if segment["section"] == "final_chorus"
        ]
        self.assertEqual(
            [segment["repeat_of"] for segment in final_chorus],
            ["www.c.01", "www.c.02", "www.c.03", "www.c.04"],
        )

    def test_public_schema_is_part_of_runtime_validation(self) -> None:
        ledgers = copy.deepcopy(self.ledgers)
        del ledgers[0]["identity_invariants"]
        with self.assertRaisesRegex(ValidationError, "schema.*identity_invariants"):
            validate_anchor_ledgers(ledgers, self.records)

    def test_ordered_source_pairs_cannot_be_swapped_or_omitted(self) -> None:
        ledgers = copy.deepcopy(self.ledgers)
        first = ledgers[0]["segments"][0]
        second = ledgers[0]["segments"][1]
        first["english_quasitranslation"], second["english_quasitranslation"] = (
            second["english_quasitranslation"],
            first["english_quasitranslation"],
        )
        with self.assertRaisesRegex(ValidationError, "paired protected source line"):
            validate_anchor_ledgers(ledgers, self.records)

        ledgers = copy.deepcopy(self.ledgers)
        del ledgers[0]["segments"][0]
        ledgers[0]["source_block"]["paired_line_count"] -= 1
        with self.assertRaisesRegex(ValidationError, "protected source has 28 pairs"):
            validate_anchor_ledgers(ledgers, self.records)

    def test_repeat_target_and_source_path_are_constrained(self) -> None:
        ledgers = copy.deepcopy(self.ledgers)
        final = next(
            segment
            for segment in ledgers[0]["segments"]
            if segment["segment_id"] == "www.fc.01"
        )
        final["repeat_of"] = "www.c.02"
        with self.assertRaisesRegex(ValidationError, "repeated source text must exactly match"):
            validate_anchor_ledgers(ledgers, self.records)

        ledgers = copy.deepcopy(self.ledgers)
        ledgers[0]["source_file"] = "../replacement.md"
        with self.assertRaisesRegex(ValidationError, "source_file"):
            validate_anchor_ledgers(ledgers, self.records)

    def test_link_aggregate_status_and_acceptance_state_are_enforced(self) -> None:
        ledgers = copy.deepcopy(self.ledgers)
        requirement = ledgers[0]["requirements"][0]
        requirement["current_record_links"].append(
            copy.deepcopy(requirement["current_record_links"][0])
        )
        with self.assertRaisesRegex(ValidationError, "duplicate link"):
            validate_anchor_ledgers(ledgers, self.records)

        ledgers = copy.deepcopy(self.ledgers)
        gap = next(item for item in ledgers[0]["requirements"] if item["status"] == "gap")
        gap["status"] = "contact_candidate"
        with self.assertRaisesRegex(ValidationError, "requires a contact-language link"):
            validate_anchor_ledgers(ledgers, self.records)

        ledgers = copy.deepcopy(self.ledgers)
        test = ledgers[0]["acceptance_tests"][0]
        test["status"] = "passing"
        test["blocker"] = None
        with self.assertRaisesRegex(ValidationError, "passing requires.*evidence"):
            validate_anchor_ledgers(ledgers, self.records)

    def test_three_person_binary_obviation_failure_is_machine_readable(self) -> None:
        lights = self.by_id["anchor.when_the_lights_learn_our_names"]
        negative = next(
            item
            for item in lights["acceptance_tests"]
            if item["test_id"] == "wll.test.reveal_negative"
        )
        self.assertIn("PROX, OBV, and another OBV", negative["condition"])
        legacy = next(
            item
            for item in lights["legacy_form_inventory"]
            if item["surface_form"] == "יוֹ / יוֹוָא"
        )
        self.assertEqual(legacy["disposition"], "reject_as_analysis")


if __name__ == "__main__":
    unittest.main()
