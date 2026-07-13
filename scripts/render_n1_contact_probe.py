"""Render the first bounded contact-language lexical probe.

The donor entries remain research ingredients. These records are separate,
revision-pinned language proposals produced by explicit contact decisions.
"""

from __future__ import annotations

import argparse
import copy
import json
import unicodedata
from pathlib import Path
from typing import Any

from judeoalgonquin.normalize import strip_hebrew_marks
from judeoalgonquin.orthography import (
    CONTACT_POINTED_PROFILE,
    assert_contact_round_trip,
)
from judeoalgonquin.records import load_records


ROOT = Path(__file__).parents[1]
ENTRIES = ROOT / "data" / "entries"
OUTPUT = ENTRIES / "n1-contact-lexicon.jsonl"
CREATED_AT = "2026-07-13T01:45:00Z"


DIRECT_SPECS = [
    {
        "id": "ja.lexeme.contact_person",
        "donor_id": "ja.lexeme.hebrew_adam_person",
        "form": "adam",
        "english": ["person", "human being"],
        "definition": "A human being, without importing the source proper-name sense.",
        "part_of_speech": "noun",
        "transformation": "Retain the ordinary Hebrew-source pronunciation after separating the human sense from the proper name.",
        "layer": "direct_contact_inheritance",
        "formation_kind": "direct_borrowing",
    },
    {
        "id": "ja.lexeme.contact_wife",
        "donor_id": "ja.lexeme.hebrew_ishah_woman",
        "form": "iša",
        "english": ["wife", "female spouse"],
        "definition": "A woman in relation to her spouse; generic woman remains a separate regional-source lexeme.",
        "part_of_speech": "noun",
        "transformation": "Apply š spelling, omit nonpronounced final he, and allocate the independently documented wife sense to avoid an unmotivated duplicate of regional oxkweew 'woman'.",
        "layer": "direct_contact_inheritance",
        "formation_kind": "semantic_reallocation",
        "additional_operation": {
            "operation": "semantic_reallocation",
            "description": "Allocate the independently sourced wife sense to contact iša while retaining generic woman as a separate regional donor question.",
        },
        "wife_evidence": True,
    },
    {
        "id": "ja.lexeme.contact_bread",
        "donor_id": "ja.lexeme.hebrew_lehem",
        "form": "lexem",
        "english": ["bread"],
        "definition": "Bread as an ordinary prepared food.",
        "part_of_speech": "noun",
        "transformation": "Merge the Hebrew-source guttural as contact x while retaining the two short e vowels.",
        "layer": "direct_contact_inheritance",
        "formation_kind": "phonological_adaptation",
    },
    {
        "id": "ja.lexeme.contact_father",
        "donor_id": "ja.lexeme.hebrew_av_father",
        "form": "aw",
        "english": ["father"],
        "definition": "A male parent, excluding ancestor, founder, divine, clerical, and figurative source senses.",
        "part_of_speech": "noun",
        "transformation": "Apply the bounded ordinary-contact change of word-final Hebrew-source v to w.",
        "layer": "direct_contact_inheritance",
        "formation_kind": "phonological_adaptation",
    },
    {
        "id": "ja.lexeme.contact_milk",
        "donor_id": "ja.lexeme.hebrew_halav_milk",
        "form": "xalaw",
        "english": ["milk"],
        "definition": "Milk as an ordinary food or drink.",
        "part_of_speech": "noun",
        "transformation": "Merge the Hebrew-source guttural as x and apply the bounded word-final v-to-w contact change.",
        "layer": "direct_contact_inheritance",
        "formation_kind": "phonological_adaptation",
    },
    {
        "id": "ja.lexeme.contact_fruit",
        "donor_id": "ja.lexeme.hebrew_peri_fruit",
        "form": "pri",
        "english": ["fruit"],
        "definition": "Edible fruit, excluding figurative result, reward, and offspring extensions.",
        "part_of_speech": "noun",
        "transformation": "Use pronunciation-oriented pri; the source written sheva does not automatically supply a contact vowel.",
        "layer": "direct_contact_inheritance",
        "formation_kind": "phonological_adaptation",
    },
    {
        "id": "ja.lexeme.contact_small",
        "donor_id": "ja.lexeme.hebrew_qatan_small",
        "form": "katan",
        "english": ["small"],
        "definition": "Small in physical size, excluding young, minor, insignificant, and grammatical source extensions.",
        "part_of_speech": "property word; predicate behavior unresolved",
        "transformation": "Realize ordinary Hebrew-source q as contact k without importing Hebrew agreement.",
        "layer": "direct_contact_inheritance",
        "formation_kind": "phonological_adaptation",
    },
    {
        "id": "ja.lexeme.contact_town",
        "donor_id": "ja.lexeme.munsee_ooteenay_town",
        "form": "ooteenay",
        "english": ["town"],
        "definition": "A town or settlement in the narrow sense supported by the donor record.",
        "part_of_speech": "noun",
        "transformation": "Lexicalize the fixed word without written internal hyphens; retain ootee-n-ay only as analysis.",
        "segmentation": "ootee-n-ay",
        "layer": "direct_contact_inheritance",
        "formation_kind": "orthographic_adaptation",
    },
    {
        "id": "ja.lexeme.contact_bed",
        "donor_id": "ja.lexeme.munsee_apiinay_bed",
        "form": "apiinay",
        "english": ["bed"],
        "definition": "A bed in the narrow sense supported by the donor record.",
        "part_of_speech": "noun",
        "transformation": "Lexicalize the fixed word without written internal hyphens; retain apii-n-ay only as analysis.",
        "segmentation": "apii-n-ay",
        "layer": "direct_contact_inheritance",
        "formation_kind": "orthographic_adaptation",
    },
    {
        "id": "ja.lexeme.contact_dress_coat",
        "donor_id": "ja.lexeme.munsee_weentakwiiwan_dress_coat",
        "form": "weentakwiiwan",
        "english": ["dress", "coat"],
        "definition": "The fixed clothing noun supported by the donor record, whose short source gloss permits dress or coat.",
        "part_of_speech": "noun",
        "transformation": "Lexicalize the fixed word without written internal hyphens; retain weent-akwiiwan only as analysis.",
        "segmentation": "weent-akwiiwan",
        "layer": "direct_contact_inheritance",
        "formation_kind": "orthographic_adaptation",
    },
    {
        "id": "ja.lexeme.contact_grape",
        "donor_id": "ja.lexeme.munsee_wiisakiim_grape",
        "form": "wiisakiim",
        "english": ["grape"],
        "definition": "A grape, with the donor analysis retained but not generalized.",
        "part_of_speech": "noun",
        "transformation": "Lexicalize the fixed word without written internal hyphens; retain wiisak-ii-m only as analysis.",
        "segmentation": "wiisak-ii-m",
        "layer": "direct_contact_inheritance",
        "formation_kind": "orthographic_adaptation",
    },
    {
        "id": "ja.lexeme.contact_plate",
        "donor_id": "ja.lexeme.munsee_pakiincrew_plate",
        "form": "pakiinčəw",
        "english": ["plate"],
        "definition": "A plate, with the donor analysis retained but not generalized.",
        "part_of_speech": "noun",
        "transformation": "Lexicalize the fixed word without written internal hyphens; retain pak-ii-nčəw only as analysis.",
        "segmentation": "pak-ii-nčəw",
        "layer": "direct_contact_inheritance",
        "formation_kind": "orthographic_adaptation",
    },
    {
        "id": "ja.lexeme.contact_cup",
        "donor_id": "ja.lexeme.munsee_tiihincrew_cup",
        "form": "tiihinčəw",
        "english": ["cup"],
        "definition": "A cup, with the donor analysis retained but not generalized.",
        "part_of_speech": "noun",
        "transformation": "Lexicalize the fixed word without written internal hyphens; retain tiih-ii-nčəw only as analysis.",
        "segmentation": "tiih-ii-nčəw",
        "layer": "direct_contact_inheritance",
        "formation_kind": "orthographic_adaptation",
        "primary_operation": "orthographic_adaptation",
        "additional_operation": {
            "operation": "semantic_reallocation",
            "description": "Select generic cup for this probe and defer the donor's more specific teacup gloss for separate review.",
        },
    },
]


HYBRID_SPECS = [
    {
        "id": "ja.lexeme.contact_fruit_dish",
        "form": "prinčəw",
        "english": ["fruit dish", "fruit bowl"],
        "definition": "A dish used to hold or serve fruit.",
        "part_of_speech": "inanimate noun candidate",
        "root_id": "ja.lexeme.contact_fruit",
        "final_id": "ja.morpheme.munsee_ncrew_dish_final",
        "segmentation": "pri-nčəw",
        "morpheme_gloss": "fruit-dish",
        "formation_process": "Combine contact Hebrew-line pri 'fruit' with the regional-source inanimate dish final -nčəw. The final is the right-edge category head.",
        "restriction": "This isolated candidate does not establish a productive host class, and the source does not attest the mixed word.",
        "domains": ["food", "kitchen", "ordinary-life"],
    },
    {
        "id": "ja.lexeme.contact_bakery",
        "form": "lexemiikaan",
        "english": ["bakery", "bread house"],
        "definition": "A building devoted to making or selling bread.",
        "part_of_speech": "inanimate noun candidate",
        "root_id": "ja.lexeme.contact_bread",
        "final_id": "ja.morpheme.munsee_iikaan_dwelling_final",
        "segmentation": "lexem-iikaan",
        "morpheme_gloss": "bread-dwelling",
        "formation_process": "Combine contact Hebrew-line lexem 'bread' with regional-source -iikaan 'dwelling, house' and propose a bounded functional-building extension. The final is the right-edge category head.",
        "restriction": "The source supports a dwelling final, not an unrestricted building classifier or the mixed bakery sense; broader functional-building use remains unlicensed.",
        "domains": ["food", "buildings", "work", "ordinary-life"],
    },
]


def _load_dependencies() -> dict[str, dict[str, Any]]:
    paths = [ENTRIES / "n1-pilot.jsonl", ENTRIES / "n1-core-lexicon.jsonl"]
    return {record["id"]: record for path in paths for record in load_records(path)}


def _nfc_tree(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_nfc_tree(item) for item in value]
    if isinstance(value, dict):
        return {key: _nfc_tree(item) for key, item in value.items()}
    return value


def _source_evidence(
    donor: dict[str, Any], sense_id: str, *, wife_evidence: bool = False
) -> list[dict[str, Any]]:
    if wife_evidence:
        return [
            {
                "source_id": "academy_hebrew_online_resources",
                "language": "Hebrew",
                "lect": "Standard Hebrew",
                "source_form": "אִשָּׁה",
                "source_meaning": "wife; female spouse",
                "grammatical_information": "The Academy terminology entry lists אִשָּׁה and רַעְיָה for English wife; source gender and inflection are not inherited.",
                "locator": "Academy Demography terminology lists אִשָּׁה and רַעְיָה for wife; https://terms.hebrew-academy.org.il/munnah/62384_1/%D7%A8%D6%B7%D7%A2%D6%B0%D7%99%D6%B8%D7%94",
                "contributor_or_speaker": "Academy of the Hebrew Language",
                "license_status": "mixed_or_unknown",
                "accessed_at": "2026-07-12",
                "confidence": "high",
                "uncertainty": "This source supports the wife sense but does not determine contact-language marriage terminology, agreement, or inflection.",
                "supports_sense_ids": [sense_id],
                "use_type": "lexical",
                "gap_reason": None,
            }
        ]
    evidence = copy.deepcopy(donor["source_evidence"])
    for item in evidence:
        item["supports_sense_ids"] = [sense_id]
    return evidence


def _history(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not evidence:
        return []
    source_ids = sorted({item["source_id"] for item in evidence})
    locators = list(dict.fromkeys(item["locator"] for item in evidence))
    return [
        {
            "claim": "The cited sources support the donor inputs; the displayed contact output and its adaptation are project design, not an attested historical form.",
            "source_ids": source_ids,
            "locator": "; ".join(locators),
            "confidence": "high",
        }
    ]


def _orthography(form: str, source_exact: str) -> dict[str, str]:
    return {
        "status": "contact_adapted",
        "profile_id": CONTACT_POINTED_PROFILE,
        "script_origin": "contact_adapted",
        "input_system": "judeo_algonquin_contact_romanization",
        "input_level": "contact_phonemic",
        "source_exact": source_exact,
        "normalized_input": form,
        "reversibility": "pointed_only",
    }


def _envelope(
    *,
    record_id: str,
    form: str,
    english: list[str],
    definition: str,
    part_of_speech: str,
    segmentation: str,
    morpheme_gloss: str,
    layer: str,
    evidence: list[dict[str, Any]],
    depends_on: list[dict[str, Any]],
    formation_kind: str,
    operations: list[dict[str, Any]],
    formation_process: str,
    design_notes: list[str],
    domains: list[str],
    source_exact: str,
    literal_translations: list[str] | None = None,
) -> dict[str, Any]:
    sense_id = f"{record_id}.sense.primary"
    if any(item["supports_sense_ids"] != [sense_id] for item in evidence):
        raise ValueError(f"{record_id}: evidence is not namespaced to the contact sense")
    dependency_ids = [record["id"] for record in depends_on]
    source_ids = sorted({item["source_id"] for item in evidence})
    tags = [
        "n1-contact-probe",
        "candidate",
        "noncanonical",
        "contact-adapted",
        "provisional-orthography",
    ]
    if layer == "contact_native_formation":
        tags.extend(["mixed-formation", "nonproductive-pattern"])
    return {
        "schema_version": 1,
        "id": record_id,
        "record_type": "lexeme",
        "revision": 1,
        "status": "candidate",
        "level": "N1",
        "forms": {
            "english": english,
            "judeo_algonquin": {
                "hebrew_script": assert_contact_round_trip(form),
                "unpointed": strip_hebrew_marks(assert_contact_round_trip(form)),
                "romanization": form,
                "segmentation": segmentation,
                "morpheme_gloss": morpheme_gloss,
                "orthography": _orthography(form, source_exact),
            },
        },
        "senses": [
            {
                "id": sense_id,
                "glosses": english,
                "definition": definition,
                "part_of_speech": part_of_speech,
                "translations": {
                    "literal": literal_translations or [],
                    "idiomatic": english,
                },
            }
        ],
        "grammatical_features": [
            "No donor-language inflection transfers unless a separate contact construction licenses it."
        ],
        "notes": {
            "translation": ["Only the stated sense is admitted by this contact probe."],
            "grammar": [
                "Nominal class, possession, number, and predicate behavior remain unresolved unless explicitly stated."
            ],
            "design": design_notes,
        },
        "formation": {
            "historical_etymology": _history(evidence),
            "formation_kind": formation_kind,
            "inputs": [
                {
                    "input_type": "language_record",
                    "input_id": record["id"],
                    "form": record["forms"]["judeo_algonquin"]["romanization"],
                    "contribution": "Revision-pinned donor or contact input.",
                }
                for record in depends_on
            ],
            "operations": operations,
            "formation_process": formation_process,
            "design_alignment": "Builds an inspectable contact lexicon in which both parent continuities affect ordinary language without inventing a false alternate history.",
        },
        "source_evidence": evidence,
        "provenance": {
            "creator_type": "model",
            "source_ids": source_ids,
            "generation_note": "Codex authored this bounded contact candidate from explicit reviewed decisions; no generative-model API call produced it.",
        },
        "relations": {
            "depends_on": dependency_ids,
            "related_to": [],
            "conflicts_with": [],
            "supersedes": [],
            "superseded_by": [],
            "dependency_revisions": {
                record["id"]: record["revision"] for record in depends_on
            },
        },
        "composition": None,
        "construction_spec": None,
        "paradigm": None,
        "metadata": {
            "registers": ["ordinary"],
            "domains": domains,
            "tags": tags,
            "creative_anchor": None,
            "lexical_layer": layer,
        },
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
        "change_note": "Created in the first bounded contact-lexicon synthesis probe.",
    }


def render() -> list[dict[str, Any]]:
    dependencies = _load_dependencies()
    records: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for spec in DIRECT_SPECS:
        donor = dependencies[spec["donor_id"]]
        sense_id = f"{spec['id']}.sense.primary"
        evidence = _source_evidence(
            donor, sense_id, wife_evidence=spec.get("wife_evidence", False)
        )
        source_exact = donor["forms"]["judeo_algonquin"]["orthography"]["source_exact"]
        record = _envelope(
            record_id=spec["id"],
            form=spec["form"],
            english=spec["english"],
            definition=spec["definition"],
            part_of_speech=spec["part_of_speech"],
            segmentation=spec.get("segmentation", spec["form"]),
            morpheme_gloss=spec["english"][0],
            layer=spec["layer"],
            evidence=evidence,
            depends_on=[donor],
            formation_kind=spec["formation_kind"],
            operations=(
                [
                    {
                        "order": 1,
                        "operation": spec.get(
                            "primary_operation",
                            "orthographic_adaptation"
                            if spec["formation_kind"] == "orthographic_adaptation"
                            else "phonological_adaptation",
                        ),
                        "description": spec["transformation"],
                    }
                ]
                + (
                    [
                        {
                            "order": 2,
                            **spec["additional_operation"],
                        }
                    ]
                    if "additional_operation" in spec
                    else []
                )
                + [
                    {
                        "order": 3 if "additional_operation" in spec else 2,
                        "operation": "transliterate",
                        "description": "Encode the reviewed contact romanization with the reversible pointed contact profile.",
                    }
                ]
            ),
            formation_process=spec["transformation"],
            design_notes=[
                spec["transformation"],
                "The donor entry remains a source ingredient; this separate record is the proposed language form.",
            ],
            domains=list(donor["metadata"]["domains"]),
            source_exact=source_exact,
            literal_translations=[],
        )
        records.append(record)
        by_id[record["id"]] = record

    for spec in HYBRID_SPECS:
        root = by_id[spec["root_id"]]
        final = dependencies[spec["final_id"]]
        evidence: list[dict[str, Any]] = []
        record = _envelope(
            record_id=spec["id"],
            form=spec["form"],
            english=spec["english"],
            definition=spec["definition"],
            part_of_speech=spec["part_of_speech"],
            segmentation=spec["segmentation"],
            morpheme_gloss=spec["morpheme_gloss"],
            layer="contact_native_formation",
            evidence=evidence,
            depends_on=[root, final],
            formation_kind="derivation",
            operations=[
                {
                    "order": 1,
                    "operation": "combine",
                    "description": spec["formation_process"],
                },
                {
                    "order": 2,
                    "operation": "transliterate",
                    "description": "Encode the resulting contact form with the reversible pointed contact profile.",
                },
            ],
            formation_process=spec["formation_process"],
            design_notes=[spec["restriction"]],
            domains=spec["domains"],
            source_exact="",
            literal_translations=[spec["morpheme_gloss"]],
        )
        record["grammatical_features"] = [
            "The right-edge regional-source final is the proposed inanimate nominal head.",
            "This record is an isolated formation candidate and does not make the pattern productive.",
        ]
        records.append(record)
        by_id[record["id"]] = record

    if len(records) != 15 or len({record["id"] for record in records}) != 15:
        raise ValueError("the contact probe must contain exactly 15 unique records")
    return [_nfc_tree(record) for record in records]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    records = render()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "records": len(records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
