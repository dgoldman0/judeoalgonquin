import copy
import hashlib
import json
import unittest
from pathlib import Path

from judeoalgonquin.evaluate import evaluate_static_place_compositions
from judeoalgonquin.orthography import decode_contact_pointed, encode_contact_pointed
from judeoalgonquin.records import (
    ValidationError,
    load_records,
    load_source_registry,
    validate_records,
)


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "entries"
SOURCES = ROOT / "references" / "sources.yaml"
REPORT = ROOT / "docs" / "reports" / "static-place-enrichment-2026-07-13.json"
TRANCHE_FILES = (
    DATA / "n1-static-place-enrichment.jsonl",
    DATA / "n1-static-place-contact.jsonl",
    DATA / "n1-static-place-grammar.jsonl",
    DATA / "n1-static-place-examples.jsonl",
)

SOURCE_LOCATIVE = "ja.construction.munsee_static_locative_examples"
SOURCE_AI = "ja.construction.munsee_ai_independent_person_number"
CONTACT_LOCATIVE = "ja.construction.contact_static_locative"
CONTACT_AI = "ja.construction.contact_ai_posture_independent"
STATIC_CLAUSE = "ja.construction.contact_static_location_clause"
STATIC_WHERE = "ja.construction.contact_static_where_question"
CONTACT_COORDINATOR = "ja.morpheme.contact_coord_we"
CONTACT_NOMINAL_COORDINATION = "ja.construction.contact_nominal_coordination"

LOCATIVE_SURFACES = {
    "road": "aaneenk",
    "ice": "mohkamiink",
    "bed": "apiineenk",
    "house": "bayitənk",
    "room": "xederənk",
    "table": "šulxanənk",
}

POSTURE_SURFACES = {
    ("be_located", "first", "singular", "not_applicable"): "nəapiim",
    ("be_located", "second", "singular", "not_applicable"): "kəapiim",
    ("be_located", "third", "singular", "not_applicable"): "apiiw",
    ("be_located", "first", "plural", "inclusive"): "kəapiihna",
    ("be_located", "first", "plural", "exclusive"): "nəapiihna",
    ("be_located", "second", "plural", "not_applicable"): "kəapiihmwa",
    ("be_located", "third", "plural", "not_applicable"): "apiiwak",
    ("sit", "first", "singular", "not_applicable"): "nələmatapiim",
    ("sit", "second", "singular", "not_applicable"): "kələmatapiim",
    ("sit", "third", "singular", "not_applicable"): "ləmatapiiw",
    ("sit", "first", "plural", "inclusive"): "kələmatapiihna",
    ("sit", "first", "plural", "exclusive"): "nələmatapiihna",
    ("sit", "second", "plural", "not_applicable"): "kələmatapiihmwa",
    ("sit", "third", "plural", "not_applicable"): "ləmatapiiwak",
    ("stand", "first", "singular", "not_applicable"): "nəniipawiim",
    ("stand", "second", "singular", "not_applicable"): "kəniipawiim",
    ("stand", "third", "singular", "not_applicable"): "niipawiiw",
    ("stand", "first", "plural", "inclusive"): "kəniipawiihna",
    ("stand", "first", "plural", "exclusive"): "nəniipawiihna",
    ("stand", "second", "plural", "not_applicable"): "kəniipawiihmwa",
    ("stand", "third", "plural", "not_applicable"): "niipawiiwak",
}

PHRASES = {
    "ja.phrase.static_on_road": ("ja.lexeme.contact_road", "aaneenk"),
    "ja.phrase.static_on_ice": ("ja.lexeme.contact_ice", "mohkamiink"),
    "ja.phrase.static_at_bed": ("ja.lexeme.contact_bed", "apiineenk"),
    "ja.phrase.static_in_house": ("ja.lexeme.contact_house", "bayitənk"),
    "ja.phrase.static_in_room": ("ja.lexeme.contact_room", "xederənk"),
    "ja.phrase.static_at_table": ("ja.lexeme.contact_table", "šulxanənk"),
}

CLAUSES = {
    "ja.sentence.static_person_in_room": "adam apiiw xederənk",
    "ja.sentence.static_child_sits_house": "yeled ləmatapiiw bayitənk",
    "ja.sentence.static_we_sit_table_inclusive": "kələmatapiihna šulxanənk",
    "ja.sentence.static_we_sit_house_exclusive": "nələmatapiihna bayitənk",
    "ja.sentence.static_child_stands_road": "yeled niipawiiw aaneenk",
    "ja.sentence.static_they_in_house": "apiiwak bayitənk",
}

QUESTIONS = {
    "ja.sentence.question_where_person": "efo adam apiiw",
    "ja.sentence.question_where_we_sit_inclusive": "efo kələmatapiihna",
}


class StaticPlaceEnrichmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_source_registry(SOURCES)
        cls.records = validate_records(
            load_records(DATA),
            source_registry=cls.registry,
        )
        cls.by_id = {record["id"]: record for record in cls.records}
        cls.tranche_ids = {
            record["id"]
            for path in TRANCHE_FILES
            for record in load_records(path)
        }

    @staticmethod
    def _record(records: list[dict], record_id: str) -> dict:
        return next(record for record in records if record["id"] == record_id)

    @staticmethod
    def _assert_finding(records: list[dict], fragment: str) -> None:
        findings = evaluate_static_place_compositions(records)
        if not any(fragment in finding for finding in findings):
            raise AssertionError(
                f"expected a finding containing {fragment!r}; got {findings!r}"
            )

    def test_tranche_is_thirty_six_manually_authored_candidates(self) -> None:
        self.assertEqual(len(self.tranche_ids), 36)
        for record_id in self.tranche_ids:
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                self.assertEqual(record["status"], "candidate")
                self.assertIn("noncanonical", record["metadata"]["tags"])
                self.assertEqual(record["provenance"]["creator_type"], "model")
                self.assertIn("manually", record["provenance"]["generation_note"].lower())

    def test_source_locative_positive(self) -> None:
        source = self.by_id[SOURCE_LOCATIVE]
        actual = {
            cell["features"]["host"]: (cell["romanization"], cell["status"])
            for cell in source["paradigm"]["cells"]
        }
        self.assertEqual(
            actual,
            {
                "road": ("aaneenk", "attested_source"),
                "ice": ("mohkamiink", "attested_source"),
            },
        )
        self.assertIn("p. 49", source["source_evidence"][0]["locator"])
        self.assertIn("exact", " ".join(source["metadata"]["tags"]))

    def test_source_locative_negative(self) -> None:
        records = copy.deepcopy(self.records)
        self._record(records, SOURCE_LOCATIVE)["paradigm"]["cells"].pop()
        self._assert_finding(records, "exactly road and ice")

        records = copy.deepcopy(self.records)
        cell = self._record(records, SOURCE_LOCATIVE)["paradigm"]["cells"][0]
        cell["status"] = "adapted_candidate"
        self._assert_finding(records, "must remain exact")

        records = copy.deepcopy(self.records)
        cell = self._record(records, SOURCE_LOCATIVE)["paradigm"]["cells"][0]
        cell["segmentation"] = "road-LOC"
        self._assert_finding(records, "source cell must remain exact")

        records = copy.deepcopy(self.records)
        source = self._record(records, "ja.morpheme.munsee_locative_enk")
        source["source_evidence"][0]["locator"] = "uncited"
        self._assert_finding(records, "cited evidence boundary must remain exact")

    def test_source_ai_positive(self) -> None:
        source = self.by_id[SOURCE_AI]
        self.assertEqual(len(source["paradigm"]["cells"]), 7)
        self.assertTrue(
            all(cell["status"] == "attested_pattern" for cell in source["paradigm"]["cells"])
        )
        self.assertIn("p. 86", source["source_evidence"][0]["locator"])
        sit = self.by_id["ja.lexeme.munsee_lematapii_sit"]
        self.assertEqual(sit["forms"]["judeo_algonquin"]["romanization"], "ləmatapii-")
        self.assertIn("p. 47", sit["source_evidence"][0]["locator"])
        stand = self.by_id["ja.lexeme.munsee_niipawii_stand"]
        self.assertIn("p. 133", stand["source_evidence"][0]["locator"])

    def test_source_ai_negative(self) -> None:
        records = copy.deepcopy(self.records)
        self._record(records, SOURCE_AI)["paradigm"]["cells"].pop()
        self._assert_finding(records, "exactly seven participant patterns")

        records = copy.deepcopy(self.records)
        self._record(records, SOURCE_AI)["paradigm"]["cells"][0]["features"]["order"] = "dependent"
        self._assert_finding(records, "independent AI attested pattern")

        records = copy.deepcopy(self.records)
        self._record(records, SOURCE_AI)["paradigm"]["cells"][0]["romanization"] = "BAD"
        self._assert_finding(records, "affix pattern and participant meaning must remain exact")

        records = copy.deepcopy(self.records)
        source = self._record(records, "ja.lexeme.munsee_lematapii_sit")
        source["forms"]["judeo_algonquin"]["romanization"] = "lamatapii-"
        self._assert_finding(records, "source form, analysis, layer, and cited evidence boundary")

    def test_contact_atomic_forms_are_true_overlays_and_round_trip(self) -> None:
        expected = {
            "ja.morpheme.contact_coord_we": "wə-",
            "ja.morpheme.contact_locative_enk": "-ənk",
            "ja.lexeme.contact_where": "efo",
            "ja.lexeme.contact_house": "bayit",
            "ja.lexeme.contact_room": "xeder",
            "ja.lexeme.contact_table": "šulxan",
            "ja.lexeme.contact_child": "yeled",
            "ja.lexeme.contact_ice": "mohkaməy",
            "ja.lexeme.contact_be_there_ai": "apii-",
            "ja.lexeme.contact_sit_ai": "ləmatapii-",
            "ja.lexeme.contact_stand_ai": "niipawii-",
        }
        for record_id, romanization in expected.items():
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                form = record["forms"]["judeo_algonquin"]
                self.assertEqual(form["romanization"], romanization)
                self.assertEqual(record["metadata"]["lexical_layer"], "direct_contact_inheritance")
                self.assertEqual(form["hebrew_script"], encode_contact_pointed(romanization))
                self.assertEqual(decode_contact_pointed(form["hebrew_script"]), romanization)
                self.assertTrue(record["relations"]["depends_on"])

        where = self.by_id["ja.lexeme.contact_where"]
        operation = where["formation"]["operations"][0]["description"]
        self.assertIn("donor ei", operation)
        question = self.by_id[STATIC_WHERE]
        self.assertIn("hebrew-lexical-integration", question["metadata"]["tags"])
        self.assertNotIn("hebrew-structural-inheritance", question["metadata"]["tags"])

    def test_contact_atomic_mutations_are_rejected(self) -> None:
        for record_id, surface in (
            ("ja.lexeme.contact_where", "eifa"),
            ("ja.lexeme.contact_sit_ai", "lamatapii-"),
            (CONTACT_COORDINATOR, "wa-"),
        ):
            with self.subTest(record=record_id):
                records = copy.deepcopy(self.records)
                record = self._record(records, record_id)
                record["forms"]["judeo_algonquin"]["romanization"] = surface
                self._assert_finding(records, "contact atomic form and revision-pinned donor overlay")

        records = copy.deepcopy(self.records)
        where = self._record(records, "ja.lexeme.contact_where")
        where["relations"]["depends_on"] = ["ja.lexeme.contact_room"]
        self._assert_finding(records, "contact atomic form and revision-pinned donor overlay")

    def test_contact_nominal_coordination_positive(self) -> None:
        coordinator = self.by_id[CONTACT_COORDINATOR]
        self.assertEqual(
            coordinator["relations"]["dependency_revisions"],
            {"ja.morpheme.hebrew_coord_we": 3},
        )
        nominal = self.by_id[CONTACT_NOMINAL_COORDINATION]
        self.assertEqual(nominal["relations"]["depends_on"], [CONTACT_COORDINATOR])
        self.assertEqual(
            nominal["relations"]["dependency_revisions"],
            {CONTACT_COORDINATOR: 1},
        )
        phrase = self.by_id["ja.phrase.perception_light_and_sound"]
        self.assertEqual(phrase["revision"], 2)
        self.assertEqual(
            phrase["composition"]["construction_ids"],
            [CONTACT_NOMINAL_COORDINATION],
        )
        self.assertEqual(
            phrase["composition"]["components"][1]["record_id"],
            CONTACT_COORDINATOR,
        )
        self.assertEqual(self.by_id["ja.construction.contact_finite_coordination"]["revision"], 2)
        for record_id in (
            "ja.sentence.anchor_we_hear_and_see",
            "ja.sentence.anchor_we_hear_and_sing",
        ):
            self.assertEqual(self.by_id[record_id]["revision"], 2)
            self.assertEqual(
                self.by_id[record_id]["composition"]["components"][1]["record_id"],
                CONTACT_COORDINATOR,
            )

    def test_contact_nominal_coordination_negative(self) -> None:
        records = copy.deepcopy(self.records)
        construction = self._record(records, CONTACT_NOMINAL_COORDINATION)
        construction["construction_spec"]["productivity"] = "productive"
        self._assert_finding(records, "ordinary contact coordination must remain limited")

        records = copy.deepcopy(self.records)
        construction = self._record(records, CONTACT_NOMINAL_COORDINATION)
        construction["metadata"]["tags"].remove("narrative-firewall")
        self._assert_finding(records, "ordinary contact coordination must remain limited")

        records = copy.deepcopy(self.records)
        construction = self._record(records, CONTACT_NOMINAL_COORDINATION)
        construction["formation"]["inputs"][0]["input_id"] = (
            "ja.morpheme.hebrew_coord_we"
        )
        construction["relations"]["depends_on"] = ["ja.morpheme.hebrew_coord_we"]
        construction["relations"]["dependency_revisions"] = {
            "ja.morpheme.hebrew_coord_we": 3
        }
        self._assert_finding(records, "exact contact coordinator dependency")

    def test_contact_locative_positive(self) -> None:
        construction = self.by_id[CONTACT_LOCATIVE]
        actual = {
            cell["features"]["host"]: cell["romanization"]
            for cell in construction["paradigm"]["cells"]
        }
        self.assertEqual(actual, LOCATIVE_SURFACES)
        self.assertEqual(construction["construction_spec"]["productivity"], "limited")
        for cell in construction["paradigm"]["cells"]:
            with self.subTest(host=cell["features"]["host"]):
                self.assertEqual(cell["status"], "adapted_candidate")
                self.assertEqual(cell["features"]["semantic_role"], "static_location")
                self.assertEqual(cell["hebrew_script"], encode_contact_pointed(cell["romanization"]))

    def test_contact_locative_negative(self) -> None:
        records = copy.deepcopy(self.records)
        self._record(records, CONTACT_LOCATIVE)["paradigm"]["cells"].pop()
        self._assert_finding(records, "exactly the six licensed hosts")

        records = copy.deepcopy(self.records)
        cell = self._record(records, CONTACT_LOCATIVE)["paradigm"]["cells"][0]
        cell["romanization"] = "aanayənk"
        self._assert_finding(records, "road surface must be aaneenk")

        records = copy.deepcopy(self.records)
        phrase = self._record(records, "ja.phrase.static_in_house")
        phrase["composition"]["components"][0]["record_id"] = "ja.lexeme.hebrew_bayit"
        self._assert_finding(records, "contact host followed by contact -ənk")

        records = copy.deepcopy(self.records)
        phrase = self._record(records, "ja.phrase.static_on_road")
        phrase["senses"][0]["translations"]["idiomatic"] = ["toward a road"]
        self._assert_finding(records, "may not claim direction or path")

        records = copy.deepcopy(self.records)
        phrase = self._record(records, "ja.phrase.static_in_house")
        phrase["composition"]["components"][0]["realization"] = "bogus"
        self._assert_finding(records, "contact host followed by contact -ənk")

        records = copy.deepcopy(self.records)
        phrase = self._record(records, "ja.phrase.static_in_house")
        phrase["senses"][0]["definition"] = "A destination inside a house."
        self._assert_finding(records, "may not claim direction or path")

    def test_contact_ai_positive(self) -> None:
        construction = self.by_id[CONTACT_AI]
        actual = {
            (
                cell["features"]["predicate"],
                cell["features"]["person"],
                cell["features"]["number"],
                cell["features"]["clusivity"],
            ): cell["romanization"]
            for cell in construction["paradigm"]["cells"]
        }
        self.assertEqual(actual, POSTURE_SURFACES)
        self.assertEqual(len(actual), 21)
        for cell in construction["paradigm"]["cells"]:
            with self.subTest(features=cell["features"]):
                self.assertEqual(cell["status"], "adapted_candidate")
                self.assertEqual(cell["features"]["order"], "independent")
                self.assertEqual(cell["features"]["class"], "AI")
                self.assertEqual(cell["hebrew_script"], encode_contact_pointed(cell["romanization"]))
        self.assertNotIn("apəw", actual.values())
        self.assertNotIn("ləmatapəw", actual.values())

    def test_contact_ai_negative(self) -> None:
        records = copy.deepcopy(self.records)
        self._record(records, CONTACT_AI)["paradigm"]["cells"].pop()
        self._assert_finding(records, "exactly twenty-one licensed cells")

        records = copy.deepcopy(self.records)
        cell = self._record(records, CONTACT_AI)["paradigm"]["cells"][0]
        cell["romanization"] = "ntapiim"
        self._assert_finding(records, "surface must be nəapiim")

        records = copy.deepcopy(self.records)
        inclusive = next(
            cell
            for cell in self._record(records, CONTACT_AI)["paradigm"]["cells"]
            if cell["features"]["clusivity"] == "inclusive"
        )
        inclusive["meaning"] = inclusive["meaning"].replace("including", "excluding")
        self._assert_finding(records, "clusivity and meaning must agree")

        records = copy.deepcopy(self.records)
        spec = self._record(records, CONTACT_AI)["construction_spec"]
        spec["allomorphy"] = [item for item in spec["allomorphy"] if "R10" not in item]
        self._assert_finding(records, "source-rule firewalls")

    def test_all_static_phrases_have_contact_components_and_round_trip(self) -> None:
        for phrase_id, (host_id, surface) in PHRASES.items():
            with self.subTest(phrase=phrase_id):
                phrase = self.by_id[phrase_id]
                components = phrase["composition"]["components"]
                self.assertEqual(phrase["composition"]["construction_ids"], [CONTACT_LOCATIVE])
                self.assertEqual(components[0]["record_id"], host_id)
                self.assertEqual(components[1]["record_id"], "ja.morpheme.contact_locative_enk")
                form = phrase["forms"]["judeo_algonquin"]
                self.assertEqual(form["romanization"], surface)
                self.assertEqual(form["hebrew_script"], encode_contact_pointed(surface))
                self.assertEqual(decode_contact_pointed(form["hebrew_script"]), surface)

    def test_static_clause_positive(self) -> None:
        for sentence_id, surface in CLAUSES.items():
            with self.subTest(sentence=sentence_id):
                sentence = self.by_id[sentence_id]
                self.assertEqual(
                    set(sentence["composition"]["construction_ids"]),
                    {CONTACT_AI, STATIC_CLAUSE},
                )
                form = sentence["forms"]["judeo_algonquin"]
                self.assertEqual(form["romanization"], surface)
                self.assertEqual(form["hebrew_script"], encode_contact_pointed(surface))
                self.assertIn("static-only", sentence["metadata"]["tags"])

    def test_static_clause_negative(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.static_person_in_room")
        sentence["composition"]["components"].reverse()
        self._assert_finding(records, "component identities, roles, or order")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.static_child_sits_house")
        sentence["forms"]["judeo_algonquin"]["romanization"] = "yeled ləmatapəw bayitənk"
        self._assert_finding(records, "surface must be yeled ləmatapiiw bayitənk")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.static_child_stands_road")
        sentence["senses"][0]["translations"]["idiomatic"] = ["A child stands toward a road."]
        self._assert_finding(records, "may not claim direction or path")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.static_they_in_house")
        sentence["metadata"]["tags"].append("wayyiqtol-derived")
        self._assert_finding(records, "may not claim narrative behavior")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.static_child_sits_house")
        sentence["senses"][0]["translations"]["idiomatic"] = [
            "A child will sit in a house."
        ]
        self._assert_finding(records, "may not claim TAM or obviation")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.static_person_in_room")
        sentence["metadata"]["tags"].append("proximate")
        self._assert_finding(records, "may not claim TAM or obviation")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.static_they_in_house")
        sentence["metadata"]["tags"].remove("tam-firewall")
        self._assert_finding(records, "requires static, TAM, narrative")

    def test_static_where_positive(self) -> None:
        for sentence_id, surface in QUESTIONS.items():
            with self.subTest(sentence=sentence_id):
                sentence = self.by_id[sentence_id]
                components = sentence["composition"]["components"]
                self.assertEqual(
                    set(sentence["composition"]["construction_ids"]),
                    {CONTACT_AI, STATIC_WHERE},
                )
                self.assertEqual(components[0]["record_id"], "ja.lexeme.contact_where")
                self.assertEqual(components[0]["realization"], "efo")
                form = sentence["forms"]["judeo_algonquin"]
                self.assertEqual(form["romanization"], surface)
                self.assertEqual(form["hebrew_script"], encode_contact_pointed(surface))

    def test_static_where_negative(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.question_where_person")
        sentence["composition"]["components"][0]["record_id"] = "ja.lexeme.hebrew_eifo_where"
        self._assert_finding(records, "efo-first component contract")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.question_where_we_sit_inclusive")
        sentence["senses"][0]["translations"]["idiomatic"] = ["Where to do we sit?"]
        self._assert_finding(records, "may ask static location only")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.question_where_person")
        sentence["composition"]["components"].append(
            {
                "order": 4,
                "record_id": "ja.phrase.static_in_house",
                "record_revision": 1,
                "sense_id": "ja.phrase.static_in_house.sense.setting",
                "role": "static locative setting",
                "realization": "bayitənk",
            }
        )
        self._assert_finding(records, "cannot state its missing locative answer")

    def test_nested_contact_hebrew_mutations_fail_validation(self) -> None:
        records = copy.deepcopy(self.records)
        construction = self._record(records, CONTACT_AI)
        construction["paradigm"]["cells"][0]["hebrew_script"] += "א"
        with self.assertRaisesRegex(ValidationError, "does not match contact encoding"):
            validate_records(records, source_registry=self.registry)

        records = copy.deepcopy(self.records)
        phrase = self._record(records, "ja.phrase.static_in_house")
        phrase["forms"]["judeo_algonquin"]["hebrew_script"] += "א"
        with self.assertRaisesRegex(ValidationError, "does not match componentwise contact encoding"):
            validate_records(records, source_registry=self.registry)

    def test_local_report_matches_tranche_and_records_zero_api_spend(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(report["record_inventory"]["records_total"], 180)
        self.assertEqual(report["record_inventory"]["new_tranche_records"], 36)
        self.assertEqual(report["paid_api"]["embedding_requests"], 0)
        self.assertEqual(report["paid_api"]["generative_requests"], 0)
        self.assertFalse(report["paid_api"]["paid_gate_enabled_after_work"])
        for path in TRANCHE_FILES:
            with self.subTest(path=path.name):
                key = f"data/entries/{path.name}"
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(report["artifact_sha256"][key], digest)

    def test_current_records_satisfy_static_place_contract(self) -> None:
        self.assertEqual(evaluate_static_place_compositions(self.records), [])


if __name__ == "__main__":
    unittest.main()
