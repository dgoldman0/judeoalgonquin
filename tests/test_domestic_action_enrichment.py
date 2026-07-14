import copy
import hashlib
import json
import unittest
from pathlib import Path

from judeoalgonquin.evaluate import evaluate_domestic_action_compositions
from judeoalgonquin.orthography import decode_contact_pointed, encode_contact_pointed
from judeoalgonquin.records import load_records, load_source_registry, validate_records


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "entries"
SOURCES = ROOT / "references" / "sources.yaml"
TRANCHE_FILES = (
    DATA / "n1-domestic-action-source.jsonl",
    DATA / "n1-domestic-action-contact.jsonl",
    DATA / "n1-domestic-action-grammar.jsonl",
    DATA / "n1-domestic-action-examples.jsonl",
)
REPORT = ROOT / "docs" / "reports" / "domestic-action-enrichment-2026-07-13.json"
POLICY = ROOT / "config" / "api-budget.json"

ABSOLUTE = "ja.construction.contact_domestic_absolute_subset"
SMALL_CHILD = "ja.construction.contact_small_child_phrase"
COACTIVITY = "ja.construction.contact_coactivity_yaxad"
EVENT_SETTING = "ja.construction.contact_domestic_event_setting"

CELL_FORMS = {
    ("eat_inanimate", "third_singular"): "miičow",
    ("eat_inanimate", "first_plural_inclusive"): "kəmiičohna",
    ("eat_inanimate", "first_plural_exclusive"): "nəmiičohna",
    ("bring_animate", "third_singular"): "peešəwaw",
    ("bring_animate", "first_plural_inclusive"): "kəpeešəwahna",
    ("bring_animate", "first_plural_exclusive"): "nəpeešəwahna",
    ("bring_inanimate", "third_singular"): "peelow",
    ("bring_inanimate", "first_plural_inclusive"): "kəpeelohna",
    ("bring_inanimate", "first_plural_exclusive"): "nəpeelohna",
}


class DomesticActionEnrichmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = validate_records(
            load_records(DATA),
            source_registry=load_source_registry(SOURCES),
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
        findings = evaluate_domestic_action_compositions(records)
        if not any(fragment in finding for finding in findings):
            raise AssertionError(
                f"expected a finding containing {fragment!r}; got {findings!r}"
            )

    def test_tranche_is_thirty_nine_manually_authored_candidates(self) -> None:
        self.assertEqual(len(self.tranche_ids), 39)
        for record_id in self.tranche_ids:
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                self.assertEqual(record["status"], "candidate")
                self.assertIn("noncanonical", record["metadata"]["tags"])
                self.assertEqual(record["provenance"]["creator_type"], "model")
                note = record["provenance"]["generation_note"].lower()
                self.assertTrue("manual" in note or "manually" in note)

    def test_complete_tranche_satisfies_composition_contracts(self) -> None:
        self.assertEqual(evaluate_domestic_action_compositions(self.records), [])

    def test_local_report_matches_current_tranche_and_paid_gate_is_closed(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(report["record_inventory"]["records_total"], 264)
        self.assertEqual(report["record_inventory"]["new_tranche_records"], 39)
        self.assertEqual(report["verification"]["tests_passed"], 217)
        self.assertEqual(
            report["manual_language_work"]["paid_generative_model_requests"], 0
        )
        self.assertEqual(report["embedding_state"]["living_snapshot_records"], 180)
        self.assertEqual(
            report["embedding_state"]["records_missing_from_semantic_snapshot"],
            84,
        )
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertFalse(policy["paid_embeddings_enabled"])
        self.assertTrue(policy["authorization_consumed"])
        for path in TRANCHE_FILES:
            relative = path.relative_to(ROOT).as_posix()
            self.assertEqual(
                report["artifact_sha256"][relative],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

        aggregate = hashlib.sha256()
        for path in sorted(DATA.rglob("*.jsonl")):
            relative = path.relative_to(DATA).as_posix()
            aggregate.update(relative.encode("utf-8"))
            aggregate.update(b"\0")
            aggregate.update(path.read_bytes())
            aggregate.update(b"\0")
        self.assertEqual(
            report["record_inventory"]["current_data_sha256"],
            aggregate.hexdigest(),
        )

    def test_source_records_preserve_printed_and_analyzed_boundaries(self) -> None:
        expected = {
            "ja.lexeme.munsee_mweh_w_eat_animate": (
                "mwəh-w-", "/mwəh-w-/; nəmohaaw /nə-mwəhw-aa-w/", "high",
            ),
            "ja.lexeme.munsee_miichii_eat_inanimate": (
                "miičii-", "/miičii-/; nəmiičiin /nə-miičii-n/", "high",
            ),
            "ja.lexeme.munsee_peeshew_bring_animate": (
                "peešəw-", "mpeešəwaaw; /nə-peešəw-aa-w/", "high",
            ),
            "ja.lexeme.munsee_peel_bring_inanimate": (
                "peel-", "mpeeloon; /nə-peel-oo-n/", "high",
            ),
            "ja.lexeme.hebrew_yahad_together": (
                "yaḥad", "יַ֫חַד", "high",
            ),
        }
        for record_id, (form, source_form, confidence) in expected.items():
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                ja = record["forms"]["judeo_algonquin"]
                evidence = record["source_evidence"][0]
                self.assertEqual(ja["romanization"], form)
                self.assertEqual(ja["orthography"]["source_exact"], source_form)
                self.assertEqual(evidence["source_form"], source_form)
                self.assertEqual(evidence["confidence"], confidence)
                self.assertEqual(record["metadata"]["lexical_layer"], "donor_candidate")

        records = copy.deepcopy(self.records)
        source = self._record(records, "ja.lexeme.munsee_peeshew_bring_animate")
        source["source_evidence"][0]["source_form"] = "/peešəw-/"
        self._assert_finding(records, "printed/analyzed boundary")

        records = copy.deepcopy(self.records)
        source = self._record(records, "ja.lexeme.hebrew_yahad_together")
        source["source_evidence"][0]["locator"] = "uncited"
        self._assert_finding(records, "printed/analyzed boundary")

    def test_contact_records_are_revision_pinned_and_reversible(self) -> None:
        expected = {
            "ja.lexeme.contact_eat_inanimate": (
                "miičii-", "ja.lexeme.munsee_miichii_eat_inanimate", 1,
            ),
            "ja.lexeme.contact_bring_animate": (
                "peešəw-", "ja.lexeme.munsee_peeshew_bring_animate", 1,
            ),
            "ja.lexeme.contact_bring_inanimate": (
                "peel-", "ja.lexeme.munsee_peel_bring_inanimate", 1,
            ),
            "ja.lexeme.contact_together": (
                "yaxad", "ja.lexeme.hebrew_yahad_together", 1,
            ),
            "ja.lexeme.contact_mother": (
                "em", "ja.lexeme.hebrew_em_mother", 2,
            ),
        }
        for record_id, (form, donor, revision) in expected.items():
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                ja = record["forms"]["judeo_algonquin"]
                self.assertEqual(ja["romanization"], form)
                self.assertEqual(ja["hebrew_script"], encode_contact_pointed(form))
                self.assertEqual(decode_contact_pointed(ja["hebrew_script"]), form)
                self.assertEqual(record["relations"]["depends_on"], [donor])
                self.assertEqual(
                    record["relations"]["dependency_revisions"], {donor: revision}
                )

        records = copy.deepcopy(self.records)
        contact = self._record(records, "ja.lexeme.contact_bring_inanimate")
        contact["relations"]["dependency_revisions"][
            "ja.lexeme.munsee_peel_bring_inanimate"
        ] = 99
        self._assert_finding(records, "revision-pinned ancestry")

        records = copy.deepcopy(self.records)
        contact = self._record(records, "ja.lexeme.contact_bring_animate")
        contact["source_evidence"][0]["grammatical_information"] = (
            "The complete contact paradigm is inherited and source-attested."
        )
        self._assert_finding(records, "adaptation caution")

        records = copy.deepcopy(self.records)
        contact = self._record(records, "ja.lexeme.contact_eat_inanimate")
        contact["formation"]["historical_etymology"][0]["claim"] = (
            "The mixed contact construction is historically attested."
        )
        self._assert_finding(records, "source-versus-project boundary")

    def test_domestic_absolute_positive_inventory(self) -> None:
        cells = self.by_id[ABSOLUTE]["paradigm"]["cells"]
        actual = {
            (cell["features"]["predicate"], cell["features"]["person_bundle"]):
                cell["romanization"]
            for cell in cells
        }
        self.assertEqual(actual, CELL_FORMS)
        self.assertEqual(len(cells), 9)

        required_examples = {
            "ja.sentence.domestic_child_eats_bread": "yeled miičow lexem",
            "ja.sentence.domestic_mother_eats_fruit": "em miičow pri",
            "ja.sentence.domestic_we_bring_child_inclusive":
                "kəpeešəwahna yeled",
            "ja.sentence.domestic_we_bring_person_exclusive":
                "nəpeešəwahna adam",
            "ja.sentence.domestic_mother_brings_child": "em peešəwaw yeled",
        }
        for record_id, surface in required_examples.items():
            with self.subTest(record=record_id):
                self.assertEqual(
                    self.by_id[record_id]["forms"]["judeo_algonquin"]["romanization"],
                    surface,
                )

    def test_domestic_absolute_negative_boundaries(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_child_brings_bread")
        sentence["composition"]["components"][1]["record_id"] = (
            "ja.lexeme.contact_bring_animate"
        )
        self._assert_finding(records, "predicate class, overt object")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_we_bring_child_inclusive")
        sentence["composition"]["components"][1]["record_id"] = (
            "ja.lexeme.contact_bread"
        )
        self._assert_finding(records, "predicate class, overt object")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_mother_eats_fruit")
        sentence["composition"]["components"].pop()
        self._assert_finding(records, "overt object")

    def test_domestic_morphophonemics(self) -> None:
        cells = self.by_id[ABSOLUTE]["paradigm"]["cells"]
        eat_cells = [
            cell for cell in cells if cell["features"]["predicate"] == "eat_inanimate"
        ]
        self.assertEqual(
            [cell["romanization"] for cell in eat_cells],
            ["miičow", "kəmiičohna", "nəmiičohna"],
        )
        self.assertTrue(
            all("miičii~o" in cell["segmentation"] for cell in eat_cells)
        )

        records = copy.deepcopy(self.records)
        construction = self._record(records, ABSOLUTE)
        construction["paradigm"]["cells"][0]["romanization"] = "miičiio-w"
        self._assert_finding(records, "nine declared class-sensitive cells")

        records = copy.deepcopy(self.records)
        construction = self._record(records, ABSOLUTE)
        construction["formation"]["operations"][2]["description"] = (
            "Concatenate every form without change."
        )
        self._assert_finding(records, "delete final ii")

        records = copy.deepcopy(self.records)
        construction = self._record(records, ABSOLUTE)
        construction["paradigm"]["cells"][0]["hebrew_script"] = "שָׁגוּי"
        self._assert_finding(records, "script, analysis, and gloss")

        records = copy.deepcopy(self.records)
        construction = self._record(records, ABSOLUTE)
        construction["construction_spec"]["host_classes"] = [
            "any stem plus any object"
        ]
        construction["construction_spec"]["restrictions"] = []
        self._assert_finding(records, "closed hosts, order")

    def test_small_child_phrase_positive(self) -> None:
        phrase = self.by_id["ja.phrase.domestic_small_child"]
        self.assertEqual(
            phrase["forms"]["judeo_algonquin"]["romanization"], "yeled katan"
        )
        self.assertEqual(
            [item["record_id"] for item in phrase["composition"]["components"]],
            ["ja.lexeme.contact_child", "ja.lexeme.contact_small"],
        )
        self.assertEqual(phrase["composition"]["construction_ids"], [SMALL_CHILD])

    def test_small_child_phrase_negative(self) -> None:
        records = copy.deepcopy(self.records)
        phrase = self._record(records, "ja.phrase.domestic_small_child")
        phrase["forms"]["judeo_algonquin"]["romanization"] = "katan yeled"
        self._assert_finding(records, "exact components, order")

        records = copy.deepcopy(self.records)
        construction = self._record(records, SMALL_CHILD)
        construction["construction_spec"]["restrictions"] = []
        self._assert_finding(records, "closed hosts, order")

    def test_coactivity_positive(self) -> None:
        expected = {
            "ja.sentence.domestic_we_eat_bread_together_inclusive":
                "kəmiičohna lexem yaxad",
            "ja.sentence.domestic_we_eat_bread_together_exclusive":
                "nəmiičohna lexem yaxad",
            "ja.sentence.domestic_we_eat_fruit_together_inclusive":
                "kəmiičohna pri yaxad",
            "ja.sentence.domestic_we_eat_fruit_together_exclusive":
                "nəmiičohna pri yaxad",
        }
        for record_id, surface in expected.items():
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                self.assertEqual(
                    record["forms"]["judeo_algonquin"]["romanization"], surface
                )
                self.assertEqual(record["composition"]["construction_ids"], [COACTIVITY])

    def test_coactivity_negative(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = self._record(
            records, "ja.sentence.domestic_we_eat_bread_together_inclusive"
        )
        sentence["composition"]["components"][0]["record_id"] = (
            "ja.sentence.domestic_child_eats_bread"
        )
        self._assert_finding(records, "derived host, boundary, clusivity")

        records = copy.deepcopy(self.records)
        sentence = self._record(
            records, "ja.sentence.domestic_we_eat_bread_together_exclusive"
        )
        sentence["forms"]["judeo_algonquin"]["romanization"] = (
            "yaxad nəmiičohna lexem"
        )
        self._assert_finding(records, "derived host, boundary, clusivity")

    def test_event_setting_positive(self) -> None:
        expected = {
            "ja.sentence.domestic_we_eat_bread_house_inclusive":
                "kəmiičohna lexem bayitənk",
            "ja.sentence.domestic_we_eat_bread_house_exclusive":
                "nəmiičohna lexem bayitənk",
            "ja.sentence.domestic_we_eat_bread_table_inclusive":
                "kəmiičohna lexem šulxanənk",
            "ja.sentence.domestic_child_eats_bread_house":
                "yeled miičow lexem bayitənk",
        }
        for record_id, surface in expected.items():
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                self.assertEqual(
                    record["forms"]["judeo_algonquin"]["romanization"], surface
                )
                self.assertEqual(
                    record["composition"]["construction_ids"], [EVENT_SETTING]
                )

    def test_event_setting_negative(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = self._record(
            records, "ja.sentence.domestic_we_eat_bread_house_inclusive"
        )
        sentence["composition"]["components"][1]["record_id"] = (
            "ja.phrase.motion_to_house"
        )
        self._assert_finding(records, "derived host, boundary, clusivity")

        records = copy.deepcopy(self.records)
        construction = self._record(records, EVENT_SETTING)
        construction["construction_spec"]["restrictions"] = [
            "Any place or directional phrase is freely admitted."
        ]
        self._assert_finding(records, "closed hosts, order")

    def test_richer_coordination_preserves_clause_boundaries_and_valency(self) -> None:
        sentence = self.by_id[
            "ja.sentence.domestic_we_eat_bread_and_drink_inclusive"
        ]
        self.assertEqual(
            [item["record_id"] for item in sentence["composition"]["components"]],
            [
                "ja.sentence.domestic_we_eat_bread_inclusive",
                "ja.morpheme.contact_coord_we",
                "ja.sentence.action_we_drink_inclusive",
            ],
        )
        self.assertIn("valency-contrast", sentence["metadata"]["tags"])

        records = copy.deepcopy(self.records)
        sentence = self._record(
            records, "ja.sentence.domestic_we_eat_bread_and_drink_inclusive"
        )
        sentence["composition"]["components"][2]["record_id"] = (
            "ja.sentence.action_we_drink_exclusive"
        )
        self._assert_finding(records, "derived host, boundary, clusivity")

    def test_meanings_component_roles_and_source_boundaries_are_guarded(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_child_eats_bread")
        sentence["forms"]["english"] = ["a child admires bread"]
        sentence["senses"][0]["definition"] = "One child admires bread."
        self._assert_finding(records, "English meaning, sense, component roles")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_child_brings_bread")
        sentence["composition"]["components"][1]["role"] = "location"
        sentence["composition"]["components"][1]["realization"] = "wrong"
        self._assert_finding(records, "component roles")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_child_eats_bread")
        sentence["source_evidence"] = [
            copy.deepcopy(
                self.by_id["ja.lexeme.munsee_miichii_eat_inanimate"][
                    "source_evidence"
                ][0]
            )
        ]
        self._assert_finding(records, "must not invent direct source evidence")

    def test_tam_narrative_direct_inverse_and_obviation_firewalls(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_we_bring_child_inclusive")
        sentence["metadata"]["tags"].remove("obviation-deferred")
        self._assert_finding(records, "defer direct/inverse and obviation")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_we_bring_child_inclusive")
        for tag in ("animate-object", "direct-inverse-deferred", "obviation-deferred"):
            sentence["metadata"]["tags"].remove(tag)
        self._assert_finding(records, "defer direct/inverse and obviation")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_mother_brings_child")
        sentence["metadata"]["tags"].remove("tam-firewall")
        self._assert_finding(records, "require TAM and narrative firewalls")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_child_eats_bread")
        sentence["forms"]["english"] = ["the child then ate bread"]
        sentence["senses"][0]["definition"] = "The child then ate bread."
        self._assert_finding(records, "may not assert TAM")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_child_eats_bread")
        sentence["metadata"]["tags"].append("inclusive")
        self._assert_finding(records, "participant and clusivity tags")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.domestic_child_eats_bread")
        sentence["metadata"]["tags"].remove("domestic-action-enrichment")
        self._assert_finding(records, "must retain its tranche tag")


if __name__ == "__main__":
    unittest.main()
