"""One-time, idempotent migration of committed fixtures and pilot records.

The migration makes script provenance explicit and replaces the inferred walking
stem with O'Meara's directly analyzable p. 130 example. It intentionally bumps
record revisions so every derived vector becomes stale through normal rules.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from judeoalgonquin.orthography import (
    COMPONENTWISE_PROFILE,
    HEBREW_RETAINED_PROFILE,
    LEGACY_UNVERIFIED_PROFILE,
    MUNSEE_TRANSPORT_PROFILE,
    PROJECT_SCHEMATIC_PROFILE,
    encode_munsee_transport,
)


ROOT = Path(__file__).parents[1]
PILOT = ROOT / "data" / "entries" / "n1-pilot.jsonl"
FIXTURE = ROOT / "tests" / "fixtures" / "creative_anchor_candidates.jsonl"
UPDATED_AT = "2026-07-12T23:30:00Z"

HEBREW_RETAINED = {
    "ja.lexeme.hebrew_bayit",
    "ja.lexeme.hebrew_mayim",
    "ja.lexeme.hebrew_lehem",
    "ja.morpheme.hebrew_coord_we",
    "ja.morpheme.hebrew_definite_ha",
}
MUNSEE_TRANSPORT = {
    "ja.lexeme.munsee_lunew_man": ("lənəw", "lənəw", "citation"),
    "ja.lexeme.munsee_asen_stone": ("asən", "asən", "citation"),
    "ja.lexeme.munsee_pemsii_walk": (
        "/pəm-əsii-w/ → pəməsəw",
        "pəməsii-",
        "morphophonemic",
    ),
    "ja.lexeme.munsee_welesii_good": (
        "/wəl-əsii-w/ → wələsəw",
        "wələsii-",
        "morphophonemic",
    ),
    "ja.morpheme.munsee_plural_ak": ("-ak", "-ak", "morphophonemic"),
    "ja.morpheme.munsee_plural_al": ("-al", "-al", "morphophonemic"),
    "ja.morpheme.munsee_third_w": ("-w", "-w", "morphophonemic"),
}
COMPONENTWISE = {
    "ja.phrase.n1_bread_and_water",
    "ja.phrase.n1_houses",
    "ja.sentence.n1_the_man_is_good",
}


def _read(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _write(path: Path, records: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def _orthography(
    *,
    status: str,
    profile_id: str,
    script_origin: str,
    input_system: str,
    input_level: str,
    source_exact: str,
    normalized_input: str,
    reversibility: str,
) -> dict[str, str]:
    return {
        "status": status,
        "profile_id": profile_id,
        "script_origin": script_origin,
        "input_system": input_system,
        "input_level": input_level,
        "source_exact": source_exact,
        "normalized_input": normalized_input,
        "reversibility": reversibility,
    }


def _repair_walking_record(record: dict[str, Any]) -> None:
    forms = record["forms"]["judeo_algonquin"]
    forms.update(
        {
            "hebrew_script": encode_munsee_transport("pəməsii-"),
            "romanization": "pəməsii-",
            "segmentation": "pəm-əsii",
            "morpheme_gloss": "along-AI",
        }
    )
    sense = record["senses"][0]
    sense["definition"] = (
        "An animate-intransitive stem meaning walk, directly recoverable from "
        "O'Meara's analyzed third-person example."
    )
    sense["part_of_speech"] = "animate intransitive verb stem"
    record["grammatical_features"] = [
        "AI stem /pəm-əsii-/; third-person /-w/ surfaces in pəməsəw.",
        "The separately cited first-person /nə-pəmsii/ → mpəmsi shows additional phonology.",
    ]
    record["notes"]["translation"] = [
        "The N1 sense is walk; no manner, destination, or habitual meaning is added."
    ]
    record["notes"]["grammar"] = [
        "The p. 130 example supplies the AI classification that the earlier p. 53 locator lacked."
    ]
    record["notes"]["design"] = [
        "The revised candidate replaces an under-sourced inferred stem with directly analyzed source morphology."
    ]
    record["formation"] = {
        "historical_etymology": [
            {
                "claim": "O'Meara prints pəməsəw and analyzes it as /pəm-əsii-w/, glossed 'he walks'.",
                "source_ids": ["omeara_delaware_stem_morphology_1990"],
                "locator": "O'Meara 1990, p. 130, §2.4.2.1, example 2.80",
                "confidence": "high",
            }
        ],
        "formation_kind": "orthographic_adaptation",
        "inputs": [
            {
                "input_type": "source_record",
                "input_id": "omeara_delaware_stem_morphology_1990",
                "form": "pəməsəw; /pəm-əsii-w/",
                "contribution": "Printed third-person surface form, AI stem analysis, and gloss.",
            },
            {
                "input_type": "project_design",
                "input_id": MUNSEE_TRANSPORT_PROFILE,
                "form": "pəməsii-",
                "contribution": "Reversible pointed transport of the analyzed source stem.",
            },
        ],
        "operations": [
            {
                "order": 1,
                "operation": "retain",
                "description": "Retain the explicitly analyzed source AI stem /pəm-əsii-/.",
            },
            {
                "order": 2,
                "operation": "transliterate",
                "description": "Apply the reversible O'Meara-to-Hebrew transport profile.",
            },
        ],
        "formation_process": "Source-stem retention plus reversible analytic script transport.",
        "design_alignment": "Provides a source-classified ordinary motion predicate without importing a full person paradigm.",
    }
    contributor = record["source_evidence"][0]["contributor_or_speaker"]
    record["source_evidence"] = [
        {
            "source_id": "omeara_delaware_stem_morphology_1990",
            "language": "Munsee Delaware",
            "lect": "Moraviantown variety",
            "source_form": "pəməsəw; /pəm-əsii-w/",
            "source_meaning": "he walks",
            "grammatical_information": "AI stem /pəm-əsii-/ with third-person /-w/ and documented surface alternation",
            "locator": "O'Meara 1990, p. 130, §2.4.2.1, example 2.80",
            "contributor_or_speaker": contributor,
            "license_status": "copyrighted",
            "accessed_at": "2026-07-12",
            "confidence": "high",
            "uncertainty": "The source example does not license a complete person or aspect paradigm.",
            "supports_sense_ids": [sense["id"]],
            "use_type": "lexical",
            "gap_reason": None,
        },
        {
            "source_id": "omeara_delaware_stem_morphology_1990",
            "language": "Munsee Delaware",
            "lect": "Moraviantown variety",
            "source_form": "/nə-pəmsii/ → mpəmsi",
            "source_meaning": "I walk",
            "grammatical_information": "First-person form under R32; this locator alone does not state the verb class",
            "locator": "O'Meara 1990, p. 53, R32 example",
            "contributor_or_speaker": contributor,
            "license_status": "copyrighted",
            "accessed_at": "2026-07-12",
            "confidence": "high",
            "uncertainty": "Used only as supporting inflectional evidence; p. 130 supplies the AI classification.",
            "supports_sense_ids": [sense["id"]],
            "use_type": "grammatical",
            "gap_reason": None,
        },
    ]


def migrate(path: Path, *, fixture: bool = False) -> bool:
    records = _read(path)
    if all("orthography" in record["forms"]["judeo_algonquin"] for record in records):
        return False

    for record in records:
        conlang = record["forms"]["judeo_algonquin"]
        record_id = record["id"]
        if fixture:
            orthography = _orthography(
                status="unverified",
                profile_id=LEGACY_UNVERIFIED_PROFILE,
                script_origin="legacy_unverified",
                input_system="legacy_creative_fixture",
                input_level="unverified",
                source_exact=conlang["hebrew_script"],
                normalized_input=conlang["romanization"],
                reversibility="unverified",
            )
        elif record_id == "ja.lexeme.munsee_pemsii_walk":
            _repair_walking_record(record)
            conlang = record["forms"]["judeo_algonquin"]
            source_exact, normalized, level = MUNSEE_TRANSPORT[record_id]
            orthography = _orthography(
                status="provisional_transport",
                profile_id=MUNSEE_TRANSPORT_PROFILE,
                script_origin="munsee_source_transport",
                input_system="omeara_1990_scholarly",
                input_level=level,
                source_exact=source_exact,
                normalized_input=normalized,
                reversibility="pointed_only",
            )
        elif record_id in HEBREW_RETAINED:
            orthography = _orthography(
                status="source_retained",
                profile_id=HEBREW_RETAINED_PROFILE,
                script_origin="retained_hebrew",
                input_system="cited_hebrew",
                input_level="source_hebrew",
                source_exact=conlang["hebrew_script"],
                normalized_input=conlang["hebrew_script"],
                reversibility="not_transduced",
            )
        elif record_id in MUNSEE_TRANSPORT:
            source_exact, normalized, level = MUNSEE_TRANSPORT[record_id]
            conlang["hebrew_script"] = encode_munsee_transport(normalized)
            conlang["romanization"] = normalized
            orthography = _orthography(
                status="provisional_transport",
                profile_id=MUNSEE_TRANSPORT_PROFILE,
                script_origin="munsee_source_transport",
                input_system="omeara_1990_scholarly",
                input_level=level,
                source_exact=source_exact,
                normalized_input=normalized,
                reversibility="pointed_only",
            )
        elif record_id in COMPONENTWISE:
            if record_id == "ja.sentence.n1_the_man_is_good":
                # Recompose the surface after consonantal w moves to doubled
                # vav in both Munsee-derived components.  Componentwise forms
                # bypass the source transducer as a whole, so this update must
                # be explicit in the one-time migration.
                conlang["hebrew_script"] = (
                    "הַ"
                    + encode_munsee_transport("lənəw")
                    + " "
                    + encode_munsee_transport("wələsəw")
                )
            orthography = _orthography(
                status="componentwise",
                profile_id=COMPONENTWISE_PROFILE,
                script_origin="componentwise",
                input_system="revision_pinned_components",
                input_level="componentwise",
                source_exact="",
                normalized_input=conlang["romanization"],
                reversibility="componentwise",
            )
        else:
            orthography = _orthography(
                status="project_schematic",
                profile_id=PROJECT_SCHEMATIC_PROFILE,
                script_origin="project_schematic",
                input_system="project_metalanguage",
                input_level="schematic",
                source_exact="",
                normalized_input=conlang["romanization"],
                reversibility="not_transduced",
            )
        conlang["orthography"] = orthography
        record["revision"] += 1
        record["updated_at"] = UPDATED_AT
        record["change_note"] = (
            "Added explicit script provenance and reversible transport metadata; "
            "source-audited walking morphology was revised where applicable."
        )

    revisions = {record["id"]: record["revision"] for record in records}
    for record in records:
        relations = record["relations"]
        relations["dependency_revisions"] = {
            dependency: revisions[dependency] for dependency in relations["depends_on"]
        }
        composition = record.get("composition")
        if composition:
            for component in composition["components"]:
                component["record_revision"] = revisions[component["record_id"]]

    _write(path, records)
    return True


def main() -> int:
    changed = [
        path
        for path, fixture in ((PILOT, False), (FIXTURE, True))
        if migrate(path, fixture=fixture)
    ]
    print(json.dumps({"changed": [str(path.relative_to(ROOT)) for path in changed]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
