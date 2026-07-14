import copy
import hashlib
import json
import unittest
from pathlib import Path

from judeoalgonquin.evaluate import evaluate_motion_action_compositions
from judeoalgonquin.orthography import decode_contact_pointed, encode_contact_pointed
from judeoalgonquin.records import load_records, load_source_registry, validate_records


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "entries"
SOURCES = ROOT / "references" / "sources.yaml"
REPORT = ROOT / "docs" / "reports" / "motion-action-enrichment-2026-07-13.json"
POLICY = ROOT / "config" / "api-budget.json"
TRANCHE_FILES = (
    DATA / "n1-motion-action-source.jsonl",
    DATA / "n1-motion-action-contact.jsonl",
    DATA / "n1-motion-action-grammar.jsonl",
    DATA / "n1-motion-action-examples.jsonl",
)

MOTION = "ja.construction.contact_ai_motion_independent"
DRINK = "ja.construction.contact_ai_drink_independent"
FIND = "ja.construction.contact_find_absolute_first_plural"
RELATOR_PHRASE = "ja.construction.contact_spatial_relator_phrase"
RELATOR_CLAUSE = "ja.construction.contact_ai_motion_relator_clause"

MOTION_SURFACES = {
    "walk": [
        "nəpəməsiim", "kəpəməsiim", "pəməsiiw", "kəpəməsiihna",
        "nəpəməsiihna", "kəpəməsiihmwa", "pəməsiiwak",
    ],
    "go_away": [
        "nəaləməsiim", "kəaləməsiim", "aləməsiiw", "kəaləməsiihna",
        "nəaləməsiihna", "kəaləməsiihmwa", "aləməsiiwak",
    ],
    "return": [
        "nəkwaxkiim", "kəkwaxkiim", "kwaxkiiw", "kəkwaxkiihna",
        "nəkwaxkiihna", "kəkwaxkiihmwa", "kwaxkiiwak",
    ],
    "go_home": [
        "nəmaačiim", "kəmaačiim", "maačiiw", "kəmaačiihna",
        "nəmaačiihna", "kəmaačiihmwa", "maačiiwak",
    ],
}
DRINK_SURFACES = [
    "nəməneem", "kəməneem", "məneew", "kəməneehna", "nəməneehna",
    "kəməneehmwa", "məneewak",
]
FIND_SURFACES = {
    ("animate", "inclusive"): "kəmoxkawahna",
    ("animate", "exclusive"): "nəmoxkawahna",
    ("inanimate", "inclusive"): "kəmoxkamohna",
    ("inanimate", "exclusive"): "nəmoxkamohna",
}


class MotionActionEnrichmentTests(unittest.TestCase):
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
        findings = evaluate_motion_action_compositions(records)
        if not any(fragment in finding for finding in findings):
            raise AssertionError(
                f"expected a finding containing {fragment!r}; got {findings!r}"
            )

    def test_tranche_is_forty_five_manually_authored_candidates(self) -> None:
        self.assertEqual(len(self.tranche_ids), 45)
        for record_id in self.tranche_ids:
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                self.assertEqual(record["status"], "candidate")
                self.assertIn("noncanonical", record["metadata"]["tags"])
                self.assertEqual(record["provenance"]["creator_type"], "model")
                note = record["provenance"]["generation_note"].lower()
                self.assertTrue("manual" in note or "manually" in note)

    def test_complete_tranche_satisfies_composition_contracts(self) -> None:
        self.assertEqual(evaluate_motion_action_compositions(self.records), [])

    def test_local_report_matches_tranche_and_paid_gate_is_closed(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(report["record_inventory"]["records_total"], 225)
        self.assertEqual(report["record_inventory"]["new_tranche_records"], 45)
        self.assertEqual(report["verification"]["tests_passed"], 193)
        self.assertEqual(report["manual_language_work"]["paid_generative_model_requests"], 0)
        self.assertEqual(report["embedding_bootstrap"]["snapshot_records"], 180)
        self.assertEqual(
            report["embedding_bootstrap"]["new_tranche_embedding_state"],
            "The 45 motion-and-action records were authored after the frozen "
            "180-record snapshot and have no stored vectors yet.",
        )
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertFalse(policy["paid_embeddings_enabled"])
        self.assertTrue(policy["authorization_consumed"])
        self.assertEqual(policy["historical_accounted_input_tokens"], 694_040)
        self.assertEqual(
            policy["ledger_path"], ".local/api-usage-ledger-next-authorization.json"
        )
        for path in TRANCHE_FILES:
            relative = path.relative_to(ROOT).as_posix()
            self.assertEqual(
                report["artifact_sha256"][relative],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

    def test_report_pins_the_historical_motion_data_tree(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        aggregate = hashlib.sha256()
        for path in sorted(DATA.rglob("*.jsonl")):
            if path.name.startswith("n1-domestic-action-"):
                continue
            relative = path.relative_to(DATA).as_posix()
            aggregate.update(relative.encode("utf-8"))
            aggregate.update(b"\0")
            aggregate.update(path.read_bytes())
            aggregate.update(b"\0")
        self.assertEqual(
            report["record_inventory"]["current_data_sha256"],
            aggregate.hexdigest(),
        )

    def test_source_records_retain_exact_evidence_boundaries(self) -> None:
        expected = {
            "ja.lexeme.hebrew_el_goal": (
                "el", "אֶל", "to; toward; motion or direction toward", "high", "BDB",
            ),
            "ja.lexeme.hebrew_min_source": (
                "min", "מִן־", "from; out of; away from; separation from", "high", "BDB",
            ),
            "ja.lexeme.hebrew_derekh_way": (
                "derekh", "דֶּרֶךְ", "way; road; path; journey", "high", "BDB",
            ),
            "ja.lexeme.munsee_alemesii_go_away": (
                "aləm-əsii-", "aləmsəw; /aləm-əsii-w/", "he goes away", "high",
                "p. 130",
            ),
            "ja.lexeme.munsee_kwaxkii_return": (
                "kwaxk-ii-", "/kwaxk-ii-w/", "he comes/goes back", "high", "p. 134",
            ),
            "ja.lexeme.munsee_maachii_go_home": (
                "maač-ii-", "/maač-ii-w/", "he goes home", "high", "p. 134",
            ),
            "ja.lexeme.munsee_menee_drink": (
                "mən-ee-", "məneew; /mən-ee-w/", "he drinks", "medium", "p. 140",
            ),
        }
        for record_id, (
            form, source_form, source_meaning, confidence, locator_fragment,
        ) in expected.items():
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                self.assertEqual(
                    record["forms"]["judeo_algonquin"]["romanization"], form
                )
                self.assertEqual(record["source_evidence"][0]["source_form"], source_form)
                if record_id.startswith("ja.lexeme.munsee_"):
                    self.assertEqual(
                        record["forms"]["judeo_algonquin"]["orthography"][
                            "source_exact"
                        ],
                        source_form,
                    )
                self.assertEqual(
                    record["source_evidence"][0]["source_meaning"], source_meaning
                )
                self.assertEqual(
                    record["source_evidence"][0]["confidence"], confidence
                )
                self.assertIn(locator_fragment, record["source_evidence"][0]["locator"])
                self.assertEqual(record["metadata"]["lexical_layer"], "donor_candidate")

        drink = self.by_id["ja.lexeme.munsee_menee_drink"]
        self.assertEqual(
            drink["forms"]["judeo_algonquin"]["morpheme_gloss"], "drink-AI"
        )
        self.assertIn(
            "segmentation of some examples is uncertain",
            drink["source_evidence"][0]["grammatical_information"],
        )

        records = copy.deepcopy(self.records)
        contact = self._record(records, "ja.lexeme.contact_return_ai")
        contact["source_evidence"][0]["source_form"] = "unprinted-fused-form"
        self._assert_finding(records, "copied orthographic source, evidence form")

        records = copy.deepcopy(self.records)
        contact = self._record(records, "ja.lexeme.contact_go_home_ai")
        contact["forms"]["judeo_algonquin"]["orthography"]["source_exact"] = (
            "/maač-ii-/"
        )
        self._assert_finding(records, "copied orthographic source, evidence form")

        records = copy.deepcopy(self.records)
        contact = self._record(records, "ja.lexeme.contact_return_ai")
        contact["source_evidence"][0]["grammatical_information"] = (
            "A fused donor surface was printed."
        )
        self._assert_finding(records, "must not present its fused stem")

        records = copy.deepcopy(self.records)
        contact_drink = self._record(records, "ja.lexeme.contact_drink_ai")
        contact_drink["source_evidence"][0]["locator"] = "uncited"
        self._assert_finding(records, "confidence, and locator")

        records = copy.deepcopy(self.records)
        contact_drink = self._record(records, "ja.lexeme.contact_drink_ai")
        contact_drink["source_evidence"][0]["grammatical_information"] = (
            "AI-final example."
        )
        self._assert_finding(records, "preserve the source segmentation caveat")

        records = copy.deepcopy(self.records)
        source_drink = self._record(records, "ja.lexeme.munsee_menee_drink")
        source_drink["forms"]["judeo_algonquin"]["morpheme_gloss"] = "drink-AF"
        self._assert_finding(records, "source interlinear drink-AI")

        records = copy.deepcopy(self.records)
        source = self._record(records, "ja.lexeme.munsee_kwaxkii_return")
        source["source_evidence"][0]["locator"] = "uncited"
        self._assert_finding(records, "evidence form, meaning, analysis")

    def test_contact_words_are_revision_pinned_and_reversible(self) -> None:
        expected = {
            "ja.lexeme.contact_el_goal": ("el", "ja.lexeme.hebrew_el_goal", 1),
            "ja.lexeme.contact_min_source": ("min", "ja.lexeme.hebrew_min_source", 1),
            "ja.lexeme.contact_derex_route": ("derex", "ja.lexeme.hebrew_derekh_way", 1),
            "ja.lexeme.contact_go_away_ai": (
                "aləməsii-", "ja.lexeme.munsee_alemesii_go_away", 1,
            ),
            "ja.lexeme.contact_return_ai": (
                "kwaxkii-", "ja.lexeme.munsee_kwaxkii_return", 1,
            ),
            "ja.lexeme.contact_go_home_ai": (
                "maačii-", "ja.lexeme.munsee_maachii_go_home", 1,
            ),
            "ja.lexeme.contact_drink_ai": (
                "mənee-", "ja.lexeme.munsee_menee_drink", 1,
            ),
            "ja.lexeme.contact_find_animate": (
                "moxkaw-", "ja.lexeme.munsee_moxk_aw_find_animate", 2,
            ),
            "ja.lexeme.contact_find_inanimate": (
                "moxkam-", "ja.lexeme.munsee_moxk_am_find_inanimate", 2,
            ),
            "ja.lexeme.contact_door": ("delet", "ja.lexeme.hebrew_delet_door", 2),
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
                if record_id in {
                    "ja.lexeme.contact_go_away_ai",
                    "ja.lexeme.contact_return_ai",
                    "ja.lexeme.contact_go_home_ai",
                    "ja.lexeme.contact_drink_ai",
                }:
                    donor_form = self.by_id[donor]["source_evidence"][0]["source_form"]
                    self.assertEqual(ja["orthography"]["source_exact"], donor_form)
        self.assertEqual(
            self.by_id["ja.lexeme.contact_derex_route"]["source_evidence"], []
        )

    def test_generic_go_and_come_remain_unresolved(self) -> None:
        for record_id in ("ja.lexeme.munsee_aa_go", "ja.lexeme.munsee_paa_come"):
            self.assertIn(
                "source-class:unresolved", self.by_id[record_id]["metadata"]["tags"]
            )
        motion_inputs = {
            item["input_id"] for item in self.by_id[MOTION]["formation"]["inputs"]
        }
        self.assertFalse(
            {"ja.lexeme.munsee_aa_go", "ja.lexeme.munsee_paa_come"}
            & motion_inputs
        )

        records = copy.deepcopy(self.records)
        self._record(records, "ja.lexeme.munsee_aa_go")["metadata"]["tags"].remove(
            "source-class:unresolved"
        )
        self._assert_finding(records, "must remain class-unresolved")

    def test_motion_paradigm_has_exactly_four_by_seven_cells(self) -> None:
        construction = self.by_id[MOTION]
        actual: dict[str, list[str]] = {}
        for cell in construction["paradigm"]["cells"]:
            actual.setdefault(cell["features"]["predicate"], []).append(
                cell["romanization"]
            )
        self.assertEqual(actual, MOTION_SURFACES)
        self.assertEqual(
            MOTION_SURFACES["walk"][3:5], ["kəpəməsiihna", "nəpəməsiihna"]
        )

        records = copy.deepcopy(self.records)
        self._record(records, MOTION)["paradigm"]["cells"].pop()
        self._assert_finding(records, "exactly the 28 declared motion cells")

        records = copy.deepcopy(self.records)
        self._record(records, MOTION)["paradigm"]["cells"][3]["romanization"] = "BAD"
        self._assert_finding(records, "28 declared motion cells")

    def test_drink_paradigm_is_seven_cells_and_objectless(self) -> None:
        construction = self.by_id[DRINK]
        self.assertEqual(
            [cell["romanization"] for cell in construction["paradigm"]["cells"]],
            DRINK_SURFACES,
        )
        self.assertIn("objectless-only", construction["metadata"]["tags"])
        records = copy.deepcopy(self.records)
        self._record(records, DRINK)["paradigm"]["cells"][0]["romanization"] = "BAD"
        self._assert_finding(records, "exactly seven objectless drink cells")

    def test_find_paradigm_and_sentences_preserve_object_class(self) -> None:
        construction = self.by_id[FIND]
        actual = {
            (cell["features"]["object_class"], cell["features"]["clusivity"]):
            cell["romanization"]
            for cell in construction["paradigm"]["cells"]
        }
        self.assertEqual(actual, FIND_SURFACES)

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.action_we_find_door_inclusive")
        sentence["composition"]["components"][0]["record_id"] = (
            "ja.lexeme.contact_find_animate"
        )
        self._assert_finding(records, "find stem, object class, clusivity, and surface")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.action_we_find_person_exclusive")
        sentence["metadata"]["tags"].remove("exclusive")
        self._assert_finding(records, "find stem, object class, clusivity, and surface")

    def test_relators_are_closed_directional_phrases_not_static_locatives(self) -> None:
        phrase_cells = self.by_id[RELATOR_PHRASE]["paradigm"]["cells"]
        clause_cells = self.by_id[RELATOR_CLAUSE]["paradigm"]["cells"]
        self.assertEqual(
            [cell["romanization"] for cell in phrase_cells],
            ["el bayit", "min bayit", "derex aanay"],
        )
        self.assertEqual(
            [cell["romanization"] for cell in clause_cells],
            [
                "yeled pəməsiiw el bayit",
                "yeled aləməsiiw min bayit",
                "adam pəməsiiw derex aanay",
            ],
        )
        self.assertFalse(
            any("ənk" in cell["romanization"] for cell in phrase_cells + clause_cells)
        )

        records = copy.deepcopy(self.records)
        self._record(records, RELATOR_PHRASE)["paradigm"]["cells"][0][
            "romanization"
        ] = "el bayitənk"
        self._assert_finding(records, "closed relator cells and bare complements")

    def test_tam_narrative_and_obviation_firewalls_are_enforced(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.motion_child_walks")
        sentence["metadata"]["tags"].remove("obviation-deferred")
        self._assert_finding(records, "must defer obviation")

        records = copy.deepcopy(self.records)
        construction = self._record(records, MOTION)
        construction["metadata"]["tags"].remove("tam-firewall")
        self._assert_finding(records, "requires TAM and narrative firewalls")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.motion_person_returns")
        sentence["forms"]["english"] = ["the person returned"]
        sentence["senses"][0]["definition"] = "The person returned."
        self._assert_finding(records, "may not assert TAM, obviation, or narrative")


if __name__ == "__main__":
    unittest.main()
