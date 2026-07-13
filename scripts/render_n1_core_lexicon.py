"""Render the independently reviewed N1 seed packets as deterministic candidate JSONL.

The seed packets contain compact source findings. This renderer adds the common
record envelope deterministically; it does not generate new forms or senses.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from judeoalgonquin.orthography import (
    HEBREW_RETAINED_PROFILE,
    MUNSEE_TRANSPORT_PROFILE,
    assert_transport_round_trip,
)


ROOT = Path(__file__).parents[1]
HEBREW_SEEDS = ROOT / "data" / "research" / "n1-core-hebrew-seeds.json"
MUNSEE_SEEDS = ROOT / "data" / "research" / "n1-core-munsee-seeds.json"
OUTPUT = ROOT / "data" / "entries" / "n1-core-lexicon.jsonl"
CREATED_AT = "2026-07-13T00:15:00Z"
DONOR_UPDATED_AT = "2026-07-13T00:50:00Z"
DONOR_CHANGE_NOTE = (
    "Classified the source-facing lexical record as a donor candidate so evidence "
    "cannot be mistaken for a finished contact-language word."
)
ACADEMY_SOURCE = "academy_hebrew_online_resources"
OMEARA_SOURCE = "omeara_delaware_stem_morphology_1990"
MUNSEE_ATTRIBUTION = (
    "The dissertation says most fieldwork was conducted with Emily Johnson, "
    "Ethel Peters, and Beulah Timothy, with lesser amounts of information from "
    "Mattie Huff, Enoch Jacobs, Peter Noah, Nellie Noah, and Rebecca Snake; it "
    "identifies all eight as Delaware speakers, and this item has no item-level "
    "speaker attribution."
)

HEBREW_ANIMATE = {
    "ja.lexeme.hebrew_adam_person",
    "ja.lexeme.hebrew_ishah_woman",
    "ja.lexeme.hebrew_yeled_child",
    "ja.lexeme.hebrew_em_mother",
    "ja.lexeme.hebrew_av_father",
    "ja.lexeme.hebrew_ahot_sister",
}
HEBREW_INANIMATE = {
    "ja.lexeme.hebrew_delet_door",
    "ja.lexeme.hebrew_heder_room",
    "ja.lexeme.hebrew_shulhan_table",
    "ja.lexeme.hebrew_kisse_chair",
}


def _read_packet(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("records"), list):
        raise ValueError(f"{path}: invalid seed packet")
    return value


def _nfc_tree(value: Any) -> Any:
    """Apply the project's storage normalization without changing source content."""

    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_nfc_tree(item) for item in value]
    if isinstance(value, dict):
        return {key: _nfc_tree(item) for key, item in value.items()}
    return value


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not result:
        raise ValueError(f"cannot form a sense slug from {value!r}")
    return result


def _base_record(
    *,
    record_id: str,
    record_type: str,
    english: list[str],
    hebrew_script: str,
    romanization: str,
    segmentation: str,
    orthography: dict[str, str],
    sense_id: str,
    definition: str,
    part_of_speech: str,
    grammatical_features: list[str],
    notes: dict[str, list[str]],
    formation: dict[str, Any],
    source_evidence: list[dict[str, Any]],
    domains: list[str],
    tags: list[str],
    revision: int = 1,
    updated_at: str = CREATED_AT,
    change_note: str = "Created in the bounded, source-reviewed N1 core lexical epoch.",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": record_id,
        "record_type": record_type,
        "revision": revision,
        "status": "candidate",
        "level": "N1",
        "forms": {
            "english": english,
            "judeo_algonquin": {
                "hebrew_script": hebrew_script,
                "romanization": romanization,
                "segmentation": segmentation,
                "morpheme_gloss": english[0],
                "orthography": orthography,
            },
        },
        "senses": [
            {
                "id": sense_id,
                "glosses": english,
                "definition": definition,
                "part_of_speech": part_of_speech,
                "translations": {"literal": [], "idiomatic": english},
            }
        ],
        "grammatical_features": grammatical_features,
        "notes": notes,
        "formation": formation,
        "source_evidence": source_evidence,
        "provenance": {
            "creator_type": "model",
            "source_ids": sorted({item["source_id"] for item in source_evidence}),
            "generation_note": (
                "Codex rendered this record deterministically from a manually reviewed "
                "source seed; no generative-model API call produced the form or sense."
            ),
        },
        "relations": {
            "depends_on": [],
            "related_to": [],
            "conflicts_with": [],
            "supersedes": [],
            "superseded_by": [],
            "dependency_revisions": {},
        },
        "composition": None,
        "construction_spec": None,
        "paradigm": None,
        "metadata": {
            "registers": ["ordinary"],
            "domains": domains,
            "tags": tags,
            "creative_anchor": None,
            "lexical_layer": "donor_candidate",
        },
        "created_at": CREATED_AT,
        "updated_at": updated_at,
        "change_note": change_note,
    }


def _render_hebrew(seed: dict[str, Any]) -> dict[str, Any]:
    record_id = seed["id"]
    source = seed["source_evidence"]
    historical = seed.get("historical_evidence")
    english = list(seed["english"]["glosses"])
    sense_id = f"{record_id}.sense.{_slug(english[0])}"
    class_tag = None
    if record_id in HEBREW_ANIMATE:
        class_tag = "pilot-class:animate"
    elif record_id in HEBREW_INANIMATE:
        class_tag = "pilot-class:inanimate"
    tags = [
        "n1-core",
        "candidate",
        "noncanonical",
        "hebrew-derived",
        "source-reviewed",
    ]
    if class_tag:
        tags.append(class_tag)
    class_note = (
        "The pilot nominal class tag is a provisional project assignment for "
        "composition testing, not a fact inherited from Hebrew."
        if class_tag
        else "No contact-language inflection or syntactic distribution is inferred from the source entry."
    )
    locator = f"{source['locator']}; {source['url']}"
    source_form = source.get("displayed_form", seed["source_form"])
    etymology_sources = [ACADEMY_SOURCE]
    etymology_locators = [locator]
    etymology_claim = (
        "The cited Academy entry supports this displayed Hebrew form and narrow "
        "source sense; this record makes no additional diachronic claim."
    )
    if historical:
        etymology_sources.append(historical["source_id"])
        etymology_locators.append(historical["locator"])
        etymology_claim = (
            "The Academy source supports the current temporal-adverb category, while "
            "the separately cited BDB entry supports the pointed historical headword; "
            "no further diachronic or contact-grammar claim is made."
        )
    orthography = {
        "status": "source_retained",
        "profile_id": HEBREW_RETAINED_PROFILE,
        "script_origin": "retained_hebrew",
        "input_system": "cited_hebrew",
        "input_level": "source_hebrew",
        "source_exact": seed["source_form"],
        "normalized_input": seed["source_form"],
        "reversibility": "not_transduced",
    }
    evidence = {
        "source_id": ACADEMY_SOURCE,
        "language": "Hebrew",
        "lect": "Standard Hebrew",
        "source_form": source_form,
        "source_meaning": "; ".join(english),
        "grammatical_information": source["source_grammar"],
        "locator": locator,
        "contributor_or_speaker": "Academy of the Hebrew Language",
        "license_status": "mixed_or_unknown",
        "accessed_at": "2026-07-12",
        "confidence": source["confidence"],
        "uncertainty": source["uncertainty"],
        "supports_sense_ids": [sense_id],
        "use_type": "grammatical" if seed["record_type"] == "morpheme" else "lexical",
        "gap_reason": None,
    }
    evidence_items = [evidence]
    if historical:
        evidence_items.append(
            {
                "source_id": historical["source_id"],
                "language": "Hebrew",
                "lect": "Biblical Hebrew",
                "source_form": historical["source_form"],
                "source_meaning": historical["source_meaning"],
                "grammatical_information": "Historical pointed lexical headword.",
                "locator": historical["locator"],
                "contributor_or_speaker": "Francis Brown, S. R. Driver, and Charles A. Briggs",
                "license_status": "public_domain_original_digital_license_version_specific",
                "accessed_at": "2026-07-12",
                "confidence": historical["confidence"],
                "uncertainty": historical["uncertainty"],
                "supports_sense_ids": [sense_id],
                "use_type": "historical",
                "gap_reason": None,
            }
        )
    formation_inputs = [
        {
            "input_type": "source_record",
            "input_id": ACADEMY_SOURCE,
            "form": source_form,
            "contribution": (
                "Cited Hebrew category, narrow sense, and source grammar."
                if historical
                else "Cited Hebrew form, narrow sense, and source grammar."
            ),
        }
    ]
    if historical:
        formation_inputs.append(
            {
                "input_type": "source_record",
                "input_id": historical["source_id"],
                "form": historical["source_form"],
                "contribution": "Separately cited historical pointing evidence.",
            }
        )
    formation = {
        "historical_etymology": [
            {
                "claim": etymology_claim,
                "source_ids": etymology_sources,
                "locator": "; ".join(etymology_locators),
                "confidence": source["confidence"],
            }
        ],
        "formation_kind": "direct_borrowing",
        "inputs": formation_inputs,
        "operations": [
            {
                "order": 1,
                "operation": "retain",
                "description": "Retain the cited Hebrew form without importing its inflection.",
            }
        ],
        "formation_process": (
            "Direct Hebrew-source candidate; the source form is retained while contact-language "
            "phonology, syntax, and inflection remain separate decisions."
        ),
        "design_alignment": (
            "Places Hebrew co-parent continuity in ordinary N1 vocabulary instead of restricting "
            "it to ritual or elevated registers."
        ),
    }
    return _base_record(
        record_id=record_id,
        record_type=seed["record_type"],
        english=english,
        hebrew_script=seed["source_form"],
        romanization=seed["romanization"],
        segmentation=seed["romanization"],
        orthography=orthography,
        sense_id=sense_id,
        definition=seed["english"]["definition"],
        part_of_speech=seed["english"]["part_of_speech"],
        grammatical_features=list(seed["grammatical_cautions"]),
        notes={
            "translation": [source["uncertainty"]],
            "grammar": [class_note],
            "design": [
                "Source retention is evidence-based language design, not a claim that the alternate history occurred."
            ],
        },
        formation=formation,
        source_evidence=evidence_items,
        domains=list(seed["domains"]),
        tags=tags,
        revision=seed.get("revision", 1) + 1,
        updated_at=DONOR_UPDATED_AT,
        change_note=DONOR_CHANGE_NOTE,
    )


def _munsee_record_id(seed: dict[str, Any]) -> str:
    prefix = "ja.seed.munsee."
    if not seed["id"].startswith(prefix):
        raise ValueError(f"unexpected Munsee seed ID {seed['id']!r}")
    return f"ja.{seed['type']}.munsee_{seed['id'][len(prefix):]}"


def _render_munsee(seed: dict[str, Any]) -> dict[str, Any]:
    record_id = _munsee_record_id(seed)
    english = [part.strip() for part in seed["english_gloss"].split(";") if part.strip()]
    sense_id = f"{record_id}.sense.{_slug(english[0])}"
    normalized = seed["normalized_transport_input"]
    hebrew_script = assert_transport_round_trip(normalized)
    input_level = (
        "morphophonemic"
        if seed["source_form"].startswith("/") or "-" in normalized
        else "citation"
    )
    source_category = seed.get("source_category") or ""
    grammatical_features = [seed["analysis"]]
    if source_category:
        grammatical_features.insert(
            0, f"O'Meara explicitly classifies this item as {source_category}."
        )
    tags = [
        "n1-core",
        "candidate",
        "noncanonical",
        "munsee-derived",
        "source-reviewed",
        "provisional-orthography",
        *[tag for tag in seed["tags"] if tag not in {"research-seed", "munsee-source"}],
    ]
    if source_category == "AN":
        tags.append("pilot-class:animate")
    elif source_category == "IN" and seed["type"] == "lexeme":
        tags.append("pilot-class:inanimate")
    # Preserve order while eliminating overlaps between the common and seed tags.
    tags = list(dict.fromkeys(tags))
    orthography = {
        "status": "provisional_transport",
        "profile_id": MUNSEE_TRANSPORT_PROFILE,
        "script_origin": "munsee_source_transport",
        "input_system": "omeara_1990_scholarly",
        "input_level": input_level,
        "source_exact": seed["source_form"],
        "normalized_input": normalized,
        "reversibility": "pointed_only",
    }
    evidence = {
        "source_id": OMEARA_SOURCE,
        "language": "Munsee Delaware",
        "lect": "Moraviantown variety",
        "source_form": seed["source_form"],
        "source_meaning": seed["english_gloss"],
        "grammatical_information": seed["analysis"],
        "locator": seed["locator"],
        "contributor_or_speaker": MUNSEE_ATTRIBUTION,
        "license_status": "copyrighted",
        "accessed_at": "2026-07-12",
        "confidence": "high",
        "uncertainty": seed["source"]["uncertainty"],
        "supports_sense_ids": [sense_id],
        "use_type": "grammatical" if seed["type"] == "morpheme" else "lexical",
        "gap_reason": None,
    }
    formation = {
        "historical_etymology": [
            {
                "claim": (
                    "O'Meara prints the cited Moraviantown Munsee item with this gloss or "
                    "analysis; no deeper or alternate historical derivation is asserted."
                ),
                "source_ids": [OMEARA_SOURCE],
                "locator": seed["locator"],
                "confidence": "high",
            }
        ],
        "formation_kind": "orthographic_adaptation",
        "inputs": [
            {
                "input_type": "source_record",
                "input_id": OMEARA_SOURCE,
                "form": seed["source_form"],
                "contribution": "Individually cited Munsee form, gloss, and printed analysis.",
            },
            {
                "input_type": "project_design",
                "input_id": MUNSEE_TRANSPORT_PROFILE,
                "form": normalized,
                "contribution": "Reversible pointed Hebrew transport for inspection and search.",
            },
        ],
        "operations": [
            {
                "order": 1,
                "operation": "retain",
                "description": "Preserve the exact cited item and its analytical level.",
            },
            {
                "order": 2,
                "operation": "transliterate",
                "description": "Apply the reversible noncanonical O'Meara-to-Hebrew transport.",
            },
        ],
        "formation_process": (
            "Manual per-entry source retention plus reversible analytic script transport; "
            "no unattested surface form or paradigm is generated."
        ),
        "design_alignment": (
            "Keeps the Hudson Valley regional Algonquian co-parent concrete and source-visible "
            "while present community guidance and canonical spelling remain open."
        ),
    }
    return _base_record(
        record_id=record_id,
        record_type=seed["type"],
        english=english,
        hebrew_script=hebrew_script,
        romanization=normalized,
        segmentation=normalized,
        orthography=orthography,
        sense_id=sense_id,
        definition=seed["definition"],
        part_of_speech=seed["part_of_speech"],
        grammatical_features=grammatical_features,
        notes={
            "translation": [seed["source"]["uncertainty"]],
            "grammar": [
                "The cited category and segmentation are retained only to the extent printed at the locator."
            ],
            "design": [
                "The Hebrew form is an analytic transport, not a canonical spelling or invented historical artifact."
            ],
        },
        formation=formation,
        source_evidence=[evidence],
        domains=list(seed["domains"]),
        tags=tags,
        revision=seed.get("revision", 1) + 1,
        updated_at=DONOR_UPDATED_AT,
        change_note=DONOR_CHANGE_NOTE,
    )


def render(hebrew_path: Path, munsee_path: Path) -> list[dict[str, Any]]:
    hebrew = _read_packet(hebrew_path)
    munsee = _read_packet(munsee_path)
    if len(hebrew["records"]) != 25 or len(munsee["records"]) != 35:
        raise ValueError("the frozen lexical envelope requires 25 Hebrew and 35 Munsee seeds")
    records = [
        *(_render_hebrew(seed) for seed in hebrew["records"]),
        *(_render_munsee(seed) for seed in munsee["records"]),
    ]
    ids = [record["id"] for record in records]
    if len(records) != 60 or len(ids) != len(set(ids)):
        raise ValueError("rendered lexical records must contain exactly 60 unique IDs")
    return [_nfc_tree(record) for record in records]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hebrew", type=Path, default=HEBREW_SEEDS)
    parser.add_argument("--munsee", type=Path, default=MUNSEE_SEEDS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    records = render(args.hebrew, args.munsee)
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
