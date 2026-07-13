import copy
import hashlib
import json
import unittest
from pathlib import Path

from judeoalgonquin.evaluate import evaluate_perception_compositions
from judeoalgonquin.orthography import decode_contact_pointed, encode_contact_pointed
from judeoalgonquin.records import (
    ValidationError,
    load_records,
    load_source_registry,
    validate_records,
)


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "entries"
TRANCHE = DATA / "n1-perception-enrichment.jsonl"
SOURCES = ROOT / "references" / "sources.yaml"
REPORT = ROOT / "docs" / "reports" / "perception-enrichment-2026-07-13.json"
POLICY = ROOT / "config" / "api-budget.json"

PERCEPTION_ABSOLUTE = "ja.construction.contact_perception_absolute_first_plural"
FINITE_COORDINATION = "ja.construction.contact_finite_coordination"
CONTACT_COORDINATOR = "ja.morpheme.contact_coord_we"
CONTACT_NOMINAL_COORDINATION = "ja.construction.contact_nominal_coordination"

EXPECTED_CELLS = {
    ("see", "animate", "inclusive", "first", "plural"): "kəneewahna",
    ("see", "animate", "exclusive", "first", "plural"): "nəneewahna",
    ("see", "inanimate", "inclusive", "first", "plural"): "kəneemohna",
    ("see", "inanimate", "exclusive", "first", "plural"): "nəneemohna",
    ("hear", "animate", "inclusive", "first", "plural"): "kəpəntawahna",
    ("hear", "animate", "exclusive", "first", "plural"): "nəpəntawahna",
    ("hear", "inanimate", "inclusive", "first", "plural"): "kəpəntamohna",
    ("hear", "inanimate", "exclusive", "first", "plural"): "nəpəntamohna",
    ("look-at", "animate", "inclusive", "first", "plural"): "kəpənawahna",
    ("look-at", "animate", "exclusive", "first", "plural"): "nəpənawahna",
    ("look-at", "inanimate", "inclusive", "first", "plural"): "kəpənamohna",
    ("look-at", "inanimate", "exclusive", "first", "plural"): "nəpənamohna",
}

LEXICAL_PAIRS = {
    "ja.lexeme.contact_see_animate": ("nee-w-", "TA", "transitive animate verb stem"),
    "ja.lexeme.contact_see_inanimate": ("nee-m-", "TI", "transitive inanimate verb stem"),
    "ja.lexeme.contact_hear_animate": ("pənt-aw-", "TA", "transitive animate verb stem"),
    "ja.lexeme.contact_hear_inanimate": ("pənt-am-", "TI", "transitive inanimate verb stem"),
    "ja.lexeme.contact_look_animate": ("pən-aw-", "TA", "transitive animate verb stem"),
    "ja.lexeme.contact_look_inanimate": ("pən-am-", "TI", "transitive inanimate verb stem"),
}

SIMPLE_SENTENCES = {
    "ja.sentence.perception_we_see_light": (
        "ja.lexeme.contact_see_inanimate",
        "ja.lexeme.contact_light",
        "indefinite inanimate object",
        "kəneemohna or",
    ),
    "ja.sentence.perception_we_see_person": (
        "ja.lexeme.contact_see_animate",
        "ja.lexeme.contact_person",
        "indefinite animate object",
        "kəneewahna adam",
    ),
    "ja.sentence.perception_we_hear_sound": (
        "ja.lexeme.contact_hear_inanimate",
        "ja.lexeme.contact_sound",
        "indefinite inanimate object",
        "kəpəntamohna kol",
    ),
    "ja.sentence.perception_we_hear_person": (
        "ja.lexeme.contact_hear_animate",
        "ja.lexeme.contact_person",
        "indefinite animate object",
        "kəpəntawahna adam",
    ),
    "ja.sentence.perception_we_look_road": (
        "ja.lexeme.contact_look_inanimate",
        "ja.lexeme.contact_road",
        "indefinite inanimate object",
        "kəpənamohna aanay",
    ),
    "ja.sentence.perception_we_look_person": (
        "ja.lexeme.contact_look_animate",
        "ja.lexeme.contact_person",
        "indefinite animate object",
        "kəpənawahna adam",
    ),
}

COORDINATED_SENTENCES = {
    "ja.sentence.anchor_we_hear_and_see": (
        "ja.sentence.perception_we_hear_sound",
        "ja.sentence.perception_we_see_light",
        "kəpəntamohna kol wə-kəneemohna or",
    ),
    "ja.sentence.anchor_we_hear_and_sing": (
        "ja.sentence.perception_we_hear_sound",
        "ja.sentence.anchor_we_sing_inclusive",
        "kəpəntamohna kol wə-kənaxkoohəmaahna",
    ),
}


class PerceptionEnrichmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_source_registry(SOURCES)
        cls.records = validate_records(
            load_records(DATA),
            source_registry=cls.registry,
        )
        cls.by_id = {record["id"]: record for record in cls.records}
        cls.tranche_ids = {record["id"] for record in load_records(TRANCHE)}

    @staticmethod
    def _record(records: list[dict], record_id: str) -> dict:
        return next(record for record in records if record["id"] == record_id)

    @staticmethod
    def _assert_finding(records: list[dict], fragment: str) -> None:
        findings = evaluate_perception_compositions(records)
        if not any(fragment in finding for finding in findings):
            raise AssertionError(
                f"expected a finding containing {fragment!r}; got {findings!r}"
            )

    def test_tranche_is_twenty_manually_authored_noncanonical_candidates(self) -> None:
        self.assertEqual(len(self.tranche_ids), 20)
        for record_id in self.tranche_ids:
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                self.assertEqual(record["status"], "candidate")
                self.assertIn("noncanonical", record["metadata"]["tags"])
                self.assertEqual(record["provenance"]["creator_type"], "model")
                self.assertIn("manually", record["provenance"]["generation_note"].lower())

    def test_historical_checkpoint_report_remains_frozen_and_paid_gate_closed(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(report["corpus"]["records_total"], 144)
        self.assertEqual(report["corpus"]["records_added"], 20)
        self.assertEqual(report["verification"]["tests_passed"], 147)
        self.assertEqual(report["embedding_refresh_dry_run"]["api_requests"], 0)
        self.assertFalse(report["embedding_refresh_dry_run"]["paid_gate_enabled"])
        self.assertFalse(json.loads(POLICY.read_text(encoding="utf-8"))["paid_embeddings_enabled"])
        self.assertEqual(
            report["corpus"]["tranche_file_sha256"],
            "09cdc27d3c8120f4a55b0bf506b6cfbdab4d949d5b6121be04ba0c77000ba706",
        )
        self.assertEqual(
            report["corpus"]["data_sha256"],
            "cdabf3b68a9a55fa286b34d8722e8cbcf111e8f88cc055ff6f57e7191136a2f4",
        )
        self.assertGreater(len(self.records), report["corpus"]["records_total"])
        self.assertNotEqual(
            report["corpus"]["tranche_file_sha256"],
            hashlib.sha256(TRANCHE.read_bytes()).hexdigest(),
        )
        aggregate = hashlib.sha256()
        for candidate in sorted(DATA.rglob("*.jsonl")):
            relative = candidate.relative_to(DATA).as_posix()
            aggregate.update(relative.encode("utf-8"))
            aggregate.update(b"\0")
            aggregate.update(candidate.read_bytes())
            aggregate.update(b"\0")
        self.assertNotEqual(report["corpus"]["data_sha256"], aggregate.hexdigest())

    def test_source_absolute_positive(self) -> None:
        source = self.by_id["ja.construction.munsee_independent_absolute"]
        cells = source["paradigm"]["cells"]
        self.assertEqual(
            {
                (cell["features"]["object_class"], cell["romanization"], cell["meaning"])
                for cell in cells
            },
            {
                ("animate", "nə-mwəhw-ahna ohpən-ak", "we eat some potatoes"),
                ("inanimate", "nə-naat-əm-ohna nəpəy", "we go after some water"),
            },
        )
        self.assertTrue(all(cell["status"] == "attested_source" for cell in cells))
        evidence = source["source_evidence"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["source_id"], "omeara_delaware_stem_morphology_1990")
        self.assertIn("pp. 89–90", evidence[0]["locator"])

    def test_source_absolute_negative(self) -> None:
        source = self.by_id["ja.construction.munsee_independent_absolute"]
        restrictions = " ".join(source["construction_spec"]["restrictions"])
        counterexamples = " ".join(source["construction_spec"]["counterexamples"])
        design = " ".join(source["notes"]["design"])
        self.assertIn("Source-facing", restrictions)
        self.assertIn("overt and indefinite", restrictions)
        self.assertIn("No contact-language or objectless surface form", restrictions)
        self.assertIn("no overt object", counterexamples)
        self.assertIn("Every contact surface extrapolation is declared separately", design)

    def test_class_sensitive_lexical_pairs_remain_bound_and_distinct(self) -> None:
        for record_id, (romanization, stem_class, part_of_speech) in LEXICAL_PAIRS.items():
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                form = record["forms"]["judeo_algonquin"]
                self.assertEqual(form["romanization"], romanization)
                self.assertEqual(record["senses"][0]["part_of_speech"], part_of_speech)
                self.assertIn(f"contact-class:{stem_class}", record["metadata"]["tags"])
                self.assertIn("bound-verb-stem", record["metadata"]["tags"])
                self.assertEqual(form["hebrew_script"], encode_contact_pointed(romanization))
                self.assertEqual(decode_contact_pointed(form["hebrew_script"]), romanization)

    def test_hear_is_not_listen_in_positive_semantics(self) -> None:
        hear_ids = {
            "ja.lexeme.contact_hear_animate",
            "ja.lexeme.contact_hear_inanimate",
            "ja.sentence.perception_we_hear_sound",
            "ja.sentence.perception_we_hear_person",
            *COORDINATED_SENTENCES,
        }
        for record_id in hear_ids:
            with self.subTest(record=record_id):
                record = self.by_id[record_id]
                asserted = " ".join(
                    [*record["forms"]["english"]]
                    + [
                        value
                        for sense in record["senses"]
                        for value in (
                            *sense["glosses"],
                            sense["definition"],
                            *sense["translations"]["literal"],
                            *sense["translations"]["idiomatic"],
                        )
                    ]
                ).lower()
                self.assertNotIn("listen", asserted)

        records = copy.deepcopy(self.records)
        hear = self._record(records, "ja.lexeme.contact_hear_inanimate")
        hear["senses"][0]["glosses"].append("listen to something")
        self._assert_finding(records, "positive semantics may claim literal hear, not listen")

    def test_perception_absolute_positive(self) -> None:
        construction = self.by_id[PERCEPTION_ABSOLUTE]
        cells = construction["paradigm"]["cells"]
        actual = {
            (
                cell["features"]["predicate"],
                cell["features"]["object_class"],
                cell["features"]["clusivity"],
                cell["features"]["person"],
                cell["features"]["number"],
            ): cell["romanization"]
            for cell in cells
        }
        self.assertEqual(actual, EXPECTED_CELLS)
        self.assertEqual(construction["construction_spec"]["productivity"], "limited")
        self.assertEqual(len(cells), 12)
        for cell in cells:
            with self.subTest(features=cell["features"]):
                self.assertEqual(cell["status"], "adapted_candidate")
                self.assertNotIn("INCL", cell["morpheme_gloss"])
                self.assertNotIn("EXCL", cell["morpheme_gloss"])
                self.assertEqual(
                    cell["hebrew_script"], encode_contact_pointed(cell["romanization"])
                )
                self.assertEqual(
                    decode_contact_pointed(cell["hebrew_script"]), cell["romanization"]
                )

    def test_perception_absolute_cell_mutations_fail(self) -> None:
        records = copy.deepcopy(self.records)
        construction = self._record(records, PERCEPTION_ABSOLUTE)
        construction["paradigm"]["cells"].pop()
        self._assert_finding(records, "exactly twelve cells")

        records = copy.deepcopy(self.records)
        construction = self._record(records, PERCEPTION_ABSOLUTE)
        cell = construction["paradigm"]["cells"][0]
        cell["romanization"] = "kəneewohna"
        self._assert_finding(records, "surface must be kəneewahna")

        records = copy.deepcopy(self.records)
        construction = self._record(records, PERCEPTION_ABSOLUTE)
        exclusive = next(
            cell
            for cell in construction["paradigm"]["cells"]
            if cell["features"]["clusivity"] == "exclusive"
        )
        exclusive["meaning"] = exclusive["meaning"].replace("excluding", "including")
        self._assert_finding(records, "clusivity and meaning must agree")

    def test_perception_sentence_object_and_class_contracts(self) -> None:
        for record_id, (stem_id, object_id, object_role, surface) in SIMPLE_SENTENCES.items():
            with self.subTest(record=record_id):
                sentence = self.by_id[record_id]
                components = sentence["composition"]["components"]
                self.assertEqual(
                    sentence["composition"]["construction_ids"], [PERCEPTION_ABSOLUTE]
                )
                self.assertEqual(
                    [component["record_id"] for component in components],
                    [stem_id, object_id],
                )
                self.assertEqual(
                    [component["role"] for component in components],
                    ["predicate stem", object_role],
                )
                self.assertEqual(sentence["forms"]["judeo_algonquin"]["romanization"], surface)
                self.assertIn("inclusive", sentence["metadata"]["tags"])
                self.assertIn(
                    f"object-class:{'animate' if ' animate ' in f' {object_role} ' and 'inanimate' not in object_role else 'inanimate'}",
                    sentence["metadata"]["tags"],
                )

    def test_perception_absolute_class_negative(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.perception_we_see_light")
        sentence["composition"]["components"][0]["record_id"] = (
            "ja.lexeme.contact_see_animate"
        )
        self._assert_finding(records, "TA/TI predicate class conflicts")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.perception_we_see_person")
        sentence["composition"]["components"][1]["record_id"] = (
            "ja.lexeme.contact_light"
        )
        self._assert_finding(records, "TA/TI predicate class conflicts")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.perception_we_look_person")
        sentence["metadata"]["tags"].append("exclusive")
        self._assert_finding(records, "structured clusivity and object-class tags")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.perception_we_look_person")
        sentence["metadata"]["tags"].append("object-class:inanimate")
        self._assert_finding(records, "structured clusivity and object-class tags")

    def test_objectless_and_surface_mutations_fail(self) -> None:
        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.perception_we_hear_sound")
        sentence["composition"]["components"].pop()
        self._assert_finding(records, "requires predicate then one overt object")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.perception_we_hear_sound")
        sentence["forms"]["judeo_algonquin"]["romanization"] = "kəpəntamahna kol"
        self._assert_finding(records, "inclusive perception surface must be kəpəntamohna kol")

    def test_finite_coordination_positive(self) -> None:
        phrase = self.by_id["ja.phrase.perception_light_and_sound"]
        components = phrase["composition"]["components"]
        self.assertEqual(
            phrase["forms"]["judeo_algonquin"]["romanization"], "or wə-kol"
        )
        self.assertEqual(
            phrase["composition"]["construction_ids"],
            [CONTACT_NOMINAL_COORDINATION],
        )
        self.assertEqual(
            [
                (component["record_id"], component["role"], component["realization"])
                for component in components
            ],
            [
                ("ja.lexeme.contact_light", "first conjunct", "or"),
                (CONTACT_COORDINATOR, "coordinator", "wə"),
                ("ja.lexeme.contact_sound", "second conjunct", "kol"),
            ],
        )

        construction = self.by_id[FINITE_COORDINATION]
        self.assertEqual(construction["construction_spec"]["productivity"], "limited")
        self.assertIn("narrative-firewall", construction["metadata"]["tags"])
        self.assertIn("wə-CLAUSE₂", construction["construction_spec"]["formalism"])
        self.assertEqual(
            construction["relations"]["depends_on"],
            [CONTACT_COORDINATOR, CONTACT_NOMINAL_COORDINATION],
        )
        self.assertEqual(
            construction["relations"]["dependency_revisions"],
            {CONTACT_COORDINATOR: 1, CONTACT_NOMINAL_COORDINATION: 1},
        )

        for record_id, (first_id, second_id, surface) in COORDINATED_SENTENCES.items():
            with self.subTest(record=record_id):
                sentence = self.by_id[record_id]
                components = sentence["composition"]["components"]
                self.assertEqual(
                    sentence["composition"]["construction_ids"], [FINITE_COORDINATION]
                )
                self.assertEqual(
                    [component["role"] for component in components],
                    ["first clause", "coordinator", "second clause"],
                )
                self.assertEqual(
                    [component["record_id"] for component in components],
                    [first_id, CONTACT_COORDINATOR, second_id],
                )
                self.assertEqual(components[1]["realization"], "wə")
                self.assertEqual(sentence["forms"]["judeo_algonquin"]["romanization"], surface)
                self.assertIn(" wə-", surface)

    def test_coordination_surface_and_coordinator_mutations_fail(self) -> None:
        records = copy.deepcopy(self.records)
        phrase = self._record(records, "ja.phrase.perception_light_and_sound")
        phrase["forms"]["judeo_algonquin"]["romanization"] = "or wə kol"
        self._assert_finding(records, "must retain proclitic wə-")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.anchor_we_hear_and_see")
        sentence["composition"]["components"][1]["realization"] = "wə-"
        self._assert_finding(records, "coordinator violate its contract")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.anchor_we_hear_and_see")
        sentence["forms"]["judeo_algonquin"]["romanization"] = (
            "kəpəntamohna kol wə kəneemohna or"
        )
        self._assert_finding(records, "surface must exactly join its two clauses with wə")

        records = copy.deepcopy(self.records)
        construction = self._record(records, FINITE_COORDINATION)
        donor_dependencies = [
            "ja.morpheme.hebrew_coord_we",
            "ja.construction.n1_nominal_coordination",
        ]
        language_inputs = [
            item
            for item in construction["formation"]["inputs"]
            if item["input_type"] == "language_record"
        ]
        for item, dependency in zip(language_inputs, donor_dependencies, strict=True):
            item["input_id"] = dependency
        construction["relations"]["depends_on"] = donor_dependencies
        construction["relations"]["dependency_revisions"] = {
            donor_dependencies[0]: 3,
            donor_dependencies[1]: 3,
        }
        self._assert_finding(records, "exact contact coordinator dependencies")

    def test_finite_coordination_clusivity_negative(self) -> None:
        records = copy.deepcopy(self.records)
        second_clause = self._record(records, "ja.sentence.anchor_we_sing_inclusive")
        tags = second_clause["metadata"]["tags"]
        tags[tags.index("inclusive")] = "exclusive"
        self._assert_finding(records, "must declare matching clusivity")

    def test_narrative_firewall(self) -> None:
        construction = self.by_id[FINITE_COORDINATION]
        restrictions = " ".join(construction["construction_spec"]["restrictions"]).lower()
        counterexamples = " ".join(
            construction["construction_spec"]["counterexamples"]
        ).lower()
        self.assertIn("no sequencing", restrictions)
        self.assertIn("wayyiqtol", restrictions)
        self.assertIn("weqatal", restrictions)
        self.assertIn("then", counterexamples)
        self.assertIn("foreground-chain", counterexamples)

        records = copy.deepcopy(self.records)
        construction = self._record(records, FINITE_COORDINATION)
        construction["senses"][0]["definition"] = (
            "Advance a foreground sequence from one clause and then the next."
        )
        self._assert_finding(records, "positive semantics cannot assert narrative-chain behavior")

        records = copy.deepcopy(self.records)
        construction = self._record(records, FINITE_COORDINATION)
        construction["metadata"]["tags"].append("weqatal-derived")
        self._assert_finding(records, "cannot enter the narrative register")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.anchor_we_hear_and_see")
        sentence["metadata"]["tags"].append("narrative")
        self._assert_finding(records, "may not assert narrative-chain semantics")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.anchor_we_hear_and_see")
        sentence["senses"][0]["definition"] = (
            "We hear a sound, then see light in a foregrounded sequence."
        )
        self._assert_finding(records, "may not assert narrative-chain semantics")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.anchor_we_hear_and_see")
        sentence["metadata"]["tags"].append("wayyiqtol-derived")
        self._assert_finding(records, "may not assert narrative-chain semantics")

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.anchor_we_hear_and_see")
        sentence["senses"][0]["definition"] = "Then, the second event occurs."
        self._assert_finding(records, "may not assert narrative-chain semantics")

    def test_all_contact_surfaces_round_trip(self) -> None:
        contact_ids = {
            "ja.lexeme.contact_sound",
            CONTACT_COORDINATOR,
            *LEXICAL_PAIRS,
            "ja.phrase.perception_light_and_sound",
            *SIMPLE_SENTENCES,
            *COORDINATED_SENTENCES,
        }
        for record_id in contact_ids:
            with self.subTest(record=record_id):
                form = self.by_id[record_id]["forms"]["judeo_algonquin"]
                self.assertEqual(form["hebrew_script"], encode_contact_pointed(form["romanization"]))
                self.assertEqual(decode_contact_pointed(form["hebrew_script"]), form["romanization"])

    def test_nested_orthography_mutations_fail_validation(self) -> None:
        records = copy.deepcopy(self.records)
        construction = self._record(records, PERCEPTION_ABSOLUTE)
        construction["paradigm"]["cells"][0]["hebrew_script"] += "א"
        with self.assertRaisesRegex(ValidationError, "does not match contact encoding"):
            validate_records(records, source_registry=self.registry)

        records = copy.deepcopy(self.records)
        sentence = self._record(records, "ja.sentence.anchor_we_hear_and_see")
        sentence["forms"]["judeo_algonquin"]["hebrew_script"] += "א"
        with self.assertRaisesRegex(
            ValidationError, "does not match componentwise contact encoding"
        ):
            validate_records(records, source_registry=self.registry)

    def test_current_records_satisfy_the_executable_contract(self) -> None:
        self.assertEqual(evaluate_perception_compositions(self.records), [])


if __name__ == "__main__":
    unittest.main()
