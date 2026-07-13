import json
import hashlib
import copy
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from judeoalgonquin.orthography import decode_contact_pointed, encode_contact_pointed
from judeoalgonquin.records import load_records, load_source_registry, validate_records
from judeoalgonquin.store import connect, index_records, search_text


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "entries"
CONTACT = DATA / "n1-contact-lexicon.jsonl"
HEBREW_DECISIONS = ROOT / "data" / "research" / "n1-hebrew-contact-decisions.json"
REGIONAL_DECISIONS = ROOT / "data" / "research" / "n1-regional-contact-decisions.json"
SOURCES = ROOT / "references" / "sources.yaml"
POLICY = ROOT / "config" / "api-budget.json"
REPORT = ROOT / "docs" / "reports" / "n1-contact-synthesis-2026-07-12.json"
DESIGN = ROOT / "docs" / "contact-phonology-and-formation.md"


class ContactProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        registry = load_source_registry(SOURCES)
        cls.records = validate_records(load_records(DATA), source_registry=registry)
        cls.by_id = {record["id"]: record for record in cls.records}
        contact_ids = {record["id"] for record in load_records(CONTACT)}
        cls.contact = [record for record in cls.records if record["id"] in contact_ids]

    def test_probe_has_declared_parent_and_mixed_balance(self) -> None:
        self.assertEqual(len(self.contact), 15)
        self.assertEqual(
            Counter(record["metadata"]["lexical_layer"] for record in self.contact),
            Counter({"direct_contact_inheritance": 13, "contact_native_formation": 2}),
        )
        direct = [
            record
            for record in self.contact
            if record["metadata"]["lexical_layer"] == "direct_contact_inheritance"
        ]
        parent = Counter(
            "hebrew"
            if ".hebrew_" in record["relations"]["depends_on"][0]
            else "regional"
            for record in direct
        )
        self.assertEqual(parent, Counter({"hebrew": 7, "regional": 6}))

    def test_all_source_facing_lexical_records_are_typed_donor_candidates(self) -> None:
        donors = [
            record
            for record in self.records
            if record["record_type"] in {"lexeme", "morpheme"}
            and any(
                item["source_id"]
                in {
                    "academy_hebrew_online_resources",
                    "bdb_1906_sefaria",
                    "omeara_delaware_stem_morphology_1990",
                }
                for item in record["source_evidence"]
            )
            and "n1-contact-probe" not in record["metadata"]["tags"]
        ]
        self.assertEqual(len(donors), 72)
        self.assertEqual(
            {record["metadata"].get("lexical_layer") for record in donors},
            {"donor_candidate"},
        )

    def test_decision_manifests_cover_the_entire_donor_inventory(self) -> None:
        hebrew = json.loads(HEBREW_DECISIONS.read_text(encoding="utf-8"))
        regional = json.loads(REGIONAL_DECISIONS.read_text(encoding="utf-8"))
        hebrew_ids = {item["source_record_id"] for item in hebrew["records"]}
        regional_ids = {item["record_id"] for item in regional["records"]}
        self.assertEqual(len(hebrew_ids), 30)
        self.assertEqual(len(regional_ids), 42)
        self.assertFalse(hebrew_ids & regional_ids)
        donor_ids = {
            record["id"]
            for record in self.records
            if record["metadata"].get("lexical_layer") == "donor_candidate"
        }
        self.assertEqual(hebrew_ids | regional_ids, donor_ids)
        for decision in hebrew["records"]:
            donor = self.by_id[decision["source_record_id"]]
            self.assertEqual(
                decision["current_form"]["romanization"],
                donor["forms"]["judeo_algonquin"]["romanization"],
            )
            proposed = decision["proposed_contact_form"]
            self.assertEqual(
                proposed["hebrew_script"],
                encode_contact_pointed(proposed["romanization"]),
            )
        for decision in regional["records"]:
            donor = self.by_id[decision["record_id"]]
            self.assertEqual(
                decision["current_form"],
                donor["forms"]["judeo_algonquin"]["romanization"],
            )
            self.assertEqual(
                decision["current_form_changes"],
                decision["current_form"] != decision["proposed_contact_form"],
            )

        wife = next(
            decision
            for decision in hebrew["records"]
            if decision["source_record_id"] == "ja.lexeme.hebrew_ishah_woman"
        )
        self.assertTrue(
            any(
                item.get("supported_sense") == "wife; female spouse"
                and "62384_1" in item.get("locator", "")
                for item in wife["exact_source_hebrew"]
            )
        )

    def test_contact_script_is_reversible_and_profile_contract_is_explicit(self) -> None:
        for record in self.contact:
            with self.subTest(record=record["id"]):
                form = record["forms"]["judeo_algonquin"]
                self.assertEqual(decode_contact_pointed(form["hebrew_script"]), form["romanization"])
                self.assertEqual(form["orthography"]["status"], "contact_adapted")
                self.assertEqual(
                    form["orthography"]["profile_id"], "contact_pointed_candidate"
                )
                self.assertIn("provisional-orthography", record["metadata"]["tags"])

        missing_layer = copy.deepcopy(self.records)
        target = next(
            record for record in missing_layer if record["id"] == "ja.lexeme.contact_bread"
        )
        del target["metadata"]["lexical_layer"]
        with self.assertRaisesRegex(
            ValueError, "contact-adapted lexical records require a contact-language layer"
        ):
            validate_records(missing_layer, source_registry=load_source_registry(SOURCES))

    def test_every_contact_record_is_revision_pinned_to_its_inputs(self) -> None:
        for record in self.contact:
            dependencies = record["relations"]["depends_on"]
            expected_count = (
                2
                if record["metadata"]["lexical_layer"] == "contact_native_formation"
                else 1
            )
            self.assertEqual(len(dependencies), expected_count)
            self.assertEqual(
                record["relations"]["dependency_revisions"],
                {record_id: self.by_id[record_id]["revision"] for record_id in dependencies},
            )

    def test_fixed_regional_words_remove_only_surface_analysis_hyphens(self) -> None:
        expected = {
            "ja.lexeme.contact_town": ("ooteenay", "ootee-n-ay"),
            "ja.lexeme.contact_bed": ("apiinay", "apii-n-ay"),
            "ja.lexeme.contact_dress_coat": ("weentakwiiwan", "weent-akwiiwan"),
            "ja.lexeme.contact_grape": ("wiisakiim", "wiisak-ii-m"),
            "ja.lexeme.contact_plate": ("pakiinčəw", "pak-ii-nčəw"),
            "ja.lexeme.contact_cup": ("tiihinčəw", "tiih-ii-nčəw"),
        }
        for record_id, (surface, segmentation) in expected.items():
            form = self.by_id[record_id]["forms"]["judeo_algonquin"]
            self.assertEqual(form["romanization"], surface)
            self.assertEqual(form["segmentation"], segmentation)

    def test_semantic_allocation_and_mixed_formations_are_not_overclaimed(self) -> None:
        wife = self.by_id["ja.lexeme.contact_wife"]
        regional_woman = self.by_id["ja.lexeme.munsee_oxkweew_woman"]
        self.assertEqual(wife["forms"]["english"][0], "wife")
        self.assertEqual(regional_woman["forms"]["english"][0], "woman")
        person = self.by_id["ja.lexeme.contact_person"]
        regional_man = self.by_id["ja.lexeme.munsee_lunew_man"]
        self.assertEqual(person["forms"]["english"][0], "person")
        self.assertEqual(regional_man["forms"]["english"][0], "man")

        fruit_dish = self.by_id["ja.lexeme.contact_fruit_dish"]
        bakery = self.by_id["ja.lexeme.contact_bakery"]
        self.assertEqual(fruit_dish["forms"]["judeo_algonquin"]["segmentation"], "pri-nčəw")
        self.assertEqual(bakery["forms"]["judeo_algonquin"]["segmentation"], "lexem-iikaan")
        expected_literals = {
            fruit_dish["id"]: ["fruit-dish"],
            bakery["id"]: ["bread-dwelling"],
        }
        for record in (fruit_dish, bakery):
            self.assertIn("nonproductive-pattern", record["metadata"]["tags"])
            self.assertEqual(record["source_evidence"], [])
            self.assertEqual(record["formation"]["historical_etymology"], [])
            self.assertEqual(
                record["senses"][0]["translations"]["literal"],
                expected_literals[record["id"]],
            )
            self.assertTrue(
                any("not" in note or "unlicensed" in note for note in record["notes"]["design"])
            )

        cup = self.by_id["ja.lexeme.contact_cup"]
        self.assertTrue(
            any(
                operation["operation"] == "semantic_reallocation"
                and "teacup" in operation["description"]
                for operation in cup["formation"]["operations"]
            )
        )

    def test_contact_aliases_are_exactly_retrievable(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            connection = connect(Path(tempdir) / "contact.sqlite3")
            self.addCleanup(connection.close)
            index_records(connection, self.records)
            for record in self.contact:
                form = record["forms"]["judeo_algonquin"]
                for alias in [*record["forms"]["english"], form["romanization"], form["hebrew_script"]]:
                    with self.subTest(record=record["id"], alias=alias):
                        exact = {
                            result["id"]
                            for result in search_text(connection, alias, limit=200)
                            if result["lexical_score"] == 100.0
                        }
                        self.assertIn(record["id"], exact)

    def test_renderer_is_byte_reproducible_and_paid_gate_stays_closed(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "contact.jsonl"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "render_n1_contact_probe.py"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(output.read_bytes(), CONTACT.read_bytes())
        self.assertFalse(
            json.loads(POLICY.read_text(encoding="utf-8"))["paid_embeddings_enabled"]
        )

    def test_local_synthesis_report_matches_data_and_records_zero_api_spend(self) -> None:
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
        self.assertEqual(report["data_sha256"], aggregate.hexdigest())
        self.assertEqual(report["data_file_sha256"], hashes)
        self.assertEqual(report["full_source_audit"]["total_decisions"], 72)
        self.assertEqual(
            report["full_source_audit"]["hebrew_manifest_sha256"],
            hashlib.sha256(HEBREW_DECISIONS.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            report["full_source_audit"]["regional_manifest_sha256"],
            hashlib.sha256(REGIONAL_DECISIONS.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            report["orthography"]["design_document_sha256"],
            hashlib.sha256(DESIGN.read_bytes()).hexdigest(),
        )
        self.assertEqual(report["local_embedding_state"]["stale_or_missing_vectors"], 107)
        self.assertFalse(report["local_embedding_state"]["refresh_authorized"])
        self.assertEqual(report["paid_api"]["embedding_requests"], 0)
        self.assertEqual(report["paid_api"]["generative_requests"], 0)
        self.assertEqual(report["paid_api"]["estimated_cost_usd"], 0.0)
        self.assertFalse(report["contains_vectors"])
        self.assertFalse(report["contains_credentials"])


if __name__ == "__main__":
    unittest.main()
