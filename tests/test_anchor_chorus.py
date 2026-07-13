import copy
import json
import unittest
from pathlib import Path

from judeoalgonquin.evaluate import evaluate_anchor_chorus_compositions
from judeoalgonquin.orthography import decode_contact_pointed, encode_contact_pointed
from judeoalgonquin.records import (
    ValidationError,
    load_records,
    load_source_registry,
    validate_records,
)


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "entries"
TRANCHE = DATA / "n1-song-chorus.jsonl"
SOURCES = ROOT / "references" / "sources.yaml"
POLICY = ROOT / "config" / "api-budget.json"


class AnchorChorusConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_source_registry(SOURCES)
        cls.records = validate_records(
            load_records(DATA),
            source_registry=cls.registry,
        )
        cls.by_id = {record["id"]: record for record in cls.records}
        cls.tranche_ids = {record["id"] for record in load_records(TRANCHE)}

    def test_tranche_is_substantive_and_noncanonical(self) -> None:
        self.assertEqual(len(self.tranche_ids), 17)
        self.assertTrue(
            all(self.by_id[record_id]["status"] == "candidate" for record_id in self.tranche_ids)
        )
        self.assertTrue(
            all(
                "noncanonical" in self.by_id[record_id]["metadata"]["tags"]
                for record_id in self.tranche_ids
            )
        )

    def test_contact_lexical_forms_round_trip(self) -> None:
        expected = {
            "ja.lexeme.contact_heart": "lew",
            "ja.lexeme.contact_light": "or",
            "ja.lexeme.contact_road": "aanay",
            "ja.lexeme.contact_walk_ai": "pəməsii-",
            "ja.lexeme.contact_good_ai": "wələsii-",
            "ja.lexeme.contact_sing_ai": "naxkoohəmaa-",
            "ja.morpheme.contact_wel_positive": "wəl-",
            "ja.lexeme.contact_welew_goodwill": "wəlew",
        }
        for record_id, romanization in expected.items():
            with self.subTest(record=record_id):
                form = self.by_id[record_id]["forms"]["judeo_algonquin"]
                self.assertEqual(form["romanization"], romanization)
                self.assertEqual(form["hebrew_script"], encode_contact_pointed(romanization))
                self.assertEqual(decode_contact_pointed(form["hebrew_script"]), romanization)

    def test_source_pattern_positive(self) -> None:
        source = self.by_id["ja.construction.munsee_ai_independent_first_plural"]
        self.assertEqual(
            {cell["romanization"] for cell in source["paradigm"]["cells"]},
            {"kə-STEM-hna", "nə-STEM-hna"},
        )
        self.assertTrue(
            all(
                cell["status"] == "attested_pattern"
                for cell in source["paradigm"]["cells"]
            )
        )

    def test_source_pattern_negative(self) -> None:
        source = self.by_id["ja.construction.munsee_ai_independent_first_plural"]
        joined = " ".join(source["construction_spec"]["restrictions"])
        self.assertIn("Source-facing", joined)
        self.assertIn("No transfer", joined)

    def test_contact_plural_positive(self) -> None:
        construction = self.by_id["ja.construction.contact_ai_first_plural"]
        expected = {
            ("walk", "inclusive"): "kəpəməsiihna",
            ("walk", "exclusive"): "nəpəməsiihna",
            ("be-good", "inclusive"): "kəwələsiihna",
            ("be-good", "exclusive"): "nəwələsiihna",
            ("sing", "inclusive"): "kənaxkoohəmaahna",
            ("sing", "exclusive"): "nənaxkoohəmaahna",
        }
        actual = {
            (cell["features"]["predicate"], cell["features"]["clusivity"]): cell["romanization"]
            for cell in construction["paradigm"]["cells"]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(construction["construction_spec"]["productivity"], "limited")
        self.assertTrue(
            all(
                cell["status"] == "adapted_candidate"
                for cell in construction["paradigm"]["cells"]
            )
        )
        for cell in construction["paradigm"]["cells"]:
            self.assertNotIn("INCL", cell["morpheme_gloss"])
            self.assertNotIn("EXCL", cell["morpheme_gloss"])
            self.assertEqual(
                cell["hebrew_script"], encode_contact_pointed(cell["romanization"])
            )
            self.assertEqual(
                decode_contact_pointed(cell["hebrew_script"]), cell["romanization"]
            )

    def test_contact_plural_negative(self) -> None:
        construction = self.by_id["ja.construction.contact_ai_first_plural"]
        restrictions = " ".join(construction["construction_spec"]["restrictions"])
        counterexamples = " ".join(construction["construction_spec"]["counterexamples"])
        self.assertIn("No TA, TI", restrictions)
        self.assertIn("discontinuous cell", restrictions)
        self.assertIn("R30", counterexamples)
        self.assertIn("no tense, aspect, or modality", restrictions)
        self.assertIn("narrative-firewall", construction["metadata"]["tags"])

    def test_goodwill_frame_positive(self) -> None:
        goodwill = self.by_id["ja.lexeme.contact_welew_goodwill"]
        self.assertEqual(goodwill["forms"]["judeo_algonquin"]["segmentation"], "wəl-lew")
        self.assertEqual(goodwill["senses"][0]["translations"]["literal"], ["good-heart"])
        self.assertEqual(goodwill["source_evidence"], [])
        self.assertEqual(
            set(goodwill["relations"]["depends_on"]),
            {"ja.morpheme.contact_wel_positive", "ja.lexeme.contact_heart"},
        )
        sentence = self.by_id["ja.sentence.anchor_we_walk_with_goodwill"]
        self.assertEqual(sentence["forms"]["judeo_algonquin"]["romanization"], "wəlew kəpəməsiihna")
        self.assertEqual(
            sentence["senses"][0]["translations"]["literal"],
            ["goodwill, we.including.you-walk"],
        )

    def test_goodwill_frame_negative(self) -> None:
        frame = self.by_id["ja.construction.contact_goodwill_manner_frame"]
        restrictions = " ".join(frame["construction_spec"]["restrictions"])
        counterexamples = " ".join(frame["construction_spec"]["counterexamples"])
        self.assertIn("Only wəlew", restrictions)
        self.assertIn("No literal plural hearts", restrictions)
        self.assertIn("Bare lew", counterexamples)
        self.assertIn("wələsii", counterexamples)

    def test_sing_continuity_is_sourced_but_not_overclaimed(self) -> None:
        donor = self.by_id["ja.lexeme.munsee_naxkoohamaa_sing"]
        contact = self.by_id["ja.lexeme.contact_sing_ai"]
        self.assertEqual(
            donor["forms"]["judeo_algonquin"]["orthography"]["source_exact"],
            "naxkooh(ə)meew; /naxkooh-əm-aa-w/",
        )
        self.assertIn("listed-stem", donor["metadata"]["tags"])
        self.assertIn("nonproductive-source-formation", contact["metadata"]["tags"])
        self.assertEqual(
            donor["notes"]["translation"],
            [
                "The source supplies only the short gloss 'he sings'; semantic range "
                "beyond that gloss is unresolved in this donor record."
            ],
        )
        self.assertIn("ringing", contact["senses"][0]["definition"])
        self.assertIn("excluded", contact["senses"][0]["definition"])

    def test_light_evidence_uses_the_noun_entry(self) -> None:
        donor = self.by_id["ja.lexeme.hebrew_or_light"]
        locator = donor["source_evidence"][0]["locator"]
        self.assertIn("%C2%B2", locator)
        contact = self.by_id["ja.lexeme.contact_light"]
        self.assertEqual(
            contact["senses"][0]["definition"],
            "Visible natural or artificial illumination.",
        )

    def test_paid_gate_remains_closed(self) -> None:
        self.assertFalse(json.loads(POLICY.read_text(encoding="utf-8"))["paid_embeddings_enabled"])

    def test_anchor_links_use_normalized_ledgers_as_authority(self) -> None:
        self.assertTrue(
            all(
                self.by_id[record_id]["metadata"]["creative_anchor"] is None
                for record_id in self.tranche_ids
            )
        )

    def test_chorus_compositions_are_executable_contracts(self) -> None:
        self.assertEqual(evaluate_anchor_chorus_compositions(self.records), [])
        for record_id in (
            "ja.sentence.anchor_we_walk_inclusive",
            "ja.sentence.anchor_we_sing_inclusive",
            "ja.sentence.anchor_we_walk_with_goodwill",
        ):
            form = self.by_id[record_id]["forms"]["judeo_algonquin"]
            self.assertNotIn("INCL", form["morpheme_gloss"])
            self.assertNotIn("EXCL", form["morpheme_gloss"])
            self.assertEqual(form["hebrew_script"], encode_contact_pointed(form["romanization"]))

    def test_required_chorus_construction_cannot_be_removed(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = next(
            item
            for item in records
            if item["id"] == "ja.sentence.anchor_we_walk_with_goodwill"
        )
        sentence["composition"]["construction_ids"].remove(
            "ja.construction.contact_goodwill_manner_frame"
        )
        self.assertTrue(
            any(
                "construction declaration mismatch" in finding
                for finding in evaluate_anchor_chorus_compositions(records)
            )
        )

    def test_excluded_host_and_frame_mutations_fail(self) -> None:
        records = copy.deepcopy(self.records)
        walk = next(
            item for item in records if item["id"] == "ja.sentence.anchor_we_walk_inclusive"
        )
        walk["composition"]["components"][0]["record_id"] = (
            "ja.lexeme.munsee_nee_m_see_inanimate"
        )
        self.assertTrue(
            any(
                "licensed predicate stem" in finding
                for finding in evaluate_anchor_chorus_compositions(records)
            )
        )

        records = copy.deepcopy(self.records)
        goodwill = next(
            item
            for item in records
            if item["id"] == "ja.sentence.anchor_we_walk_with_goodwill"
        )
        goodwill["composition"]["components"][0]["record_id"] = "ja.lexeme.contact_heart"
        self.assertTrue(
            any(
                "sole first goodwill-frame element" in finding
                for finding in evaluate_anchor_chorus_compositions(records)
            )
        )

    def test_exclusive_surface_cannot_carry_inclusive_meaning(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = next(
            item for item in records if item["id"] == "ja.sentence.anchor_we_walk_inclusive"
        )
        sentence["forms"]["judeo_algonquin"]["romanization"] = "nəpəməsiihna"
        self.assertTrue(
            any(
                "inclusive chorus surface" in finding
                for finding in evaluate_anchor_chorus_compositions(records)
            )
        )

        records = copy.deepcopy(self.records)
        construction = next(
            item
            for item in records
            if item["id"] == "ja.construction.contact_ai_first_plural"
        )
        exclusive = next(
            cell
            for cell in construction["paradigm"]["cells"]
            if cell["features"] == {"predicate": "walk", "clusivity": "exclusive"}
        )
        exclusive["meaning"] = "we, including the addressee, walk"
        self.assertTrue(
            any(
                "clusivity and meaning must agree" in finding
                for finding in evaluate_anchor_chorus_compositions(records)
            )
        )

    def test_nested_contact_orthography_and_register_mutations_fail(self) -> None:
        records = copy.deepcopy(self.records)
        construction = next(
            item
            for item in records
            if item["id"] == "ja.construction.contact_ai_first_plural"
        )
        construction["paradigm"]["cells"][0]["hebrew_script"] += "א"
        with self.assertRaisesRegex(ValidationError, "does not match contact encoding"):
            validate_records(records, source_registry=self.registry)

        records = copy.deepcopy(self.records)
        sentence = next(
            item for item in records if item["id"] == "ja.sentence.anchor_we_walk_inclusive"
        )
        sentence["forms"]["judeo_algonquin"]["hebrew_script"] += "א"
        with self.assertRaisesRegex(
            ValidationError, "does not match componentwise contact encoding"
        ):
            validate_records(records, source_registry=self.registry)

        records = copy.deepcopy(self.records)
        sentence = next(
            item for item in records if item["id"] == "ja.sentence.anchor_we_walk_inclusive"
        )
        sentence["metadata"]["registers"] = ["lyrical"]
        with self.assertRaisesRegex(ValidationError, "unknown labels"):
            validate_records(records, source_registry=self.registry)


if __name__ == "__main__":
    unittest.main()
