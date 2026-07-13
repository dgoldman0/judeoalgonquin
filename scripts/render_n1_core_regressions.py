"""Render the frozen N1 composition regressions from revision-pinned records."""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from typing import Any

from judeoalgonquin.orthography import COMPONENTWISE_PROFILE, encode_munsee_transport


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "entries"
OUTPUT = DATA / "n1-core-regressions.jsonl"
CREATED_AT = "2026-07-13T00:20:00Z"
DONOR_REFRESHED_AT = "2026-07-13T00:51:00Z"

COORDINATION = "ja.construction.n1_nominal_coordination"
DEFINITE = "ja.construction.n1_definite_prefix"
CLASS_PLURAL = "ja.construction.n1_class_plural"
AI_THIRD = "ja.construction.n1_ai_third_predicate"
CONTACT_CLAUSE = "ja.construction.n1_contact_subject_predicate"
COORDINATOR = "ja.morpheme.hebrew_coord_we"
ARTICLE = "ja.morpheme.hebrew_definite_ha"
PLURAL_INANIMATE = "ja.morpheme.munsee_plural_al"
THIRD = "ja.morpheme.munsee_third_w"
POST_EMBEDDING_REVISED = {
    "ja.phrase.n1_woman_and_child",
    "ja.phrase.n1_the_woman",
    "ja.sentence.n1_the_woman_walks",
    "ja.sentence.n1_the_woman_is_good",
}

COORDINATIONS = [
    (
        "ja.phrase.n1_mother_and_father",
        "ja.lexeme.hebrew_em_mother",
        "ja.lexeme.hebrew_av_father",
        "mother and father",
    ),
    (
        "ja.phrase.n1_woman_and_child",
        "ja.lexeme.hebrew_ishah_woman",
        "ja.lexeme.hebrew_yeled_child",
        "woman and child",
    ),
    (
        "ja.phrase.n1_bread_and_milk",
        "ja.lexeme.hebrew_lehem",
        "ja.lexeme.hebrew_halav_milk",
        "bread and milk",
    ),
    (
        "ja.phrase.n1_fruit_and_water",
        "ja.lexeme.hebrew_peri_fruit",
        "ja.lexeme.hebrew_mayim",
        "fruit and water",
    ),
]

DEFINITES = [
    ("ja.phrase.n1_the_woman", "ja.lexeme.hebrew_ishah_woman", "the woman"),
    ("ja.phrase.n1_the_child", "ja.lexeme.hebrew_yeled_child", "the child"),
]

PLURALS = [
    ("ja.phrase.n1_doors", "ja.lexeme.hebrew_delet_door", "doors"),
    ("ja.phrase.n1_chairs", "ja.lexeme.hebrew_kisse_chair", "chairs"),
]

SENTENCES = [
    (
        "ja.sentence.n1_the_woman_walks",
        "ja.lexeme.hebrew_ishah_woman",
        "ja.lexeme.munsee_pemsii_walk",
        "pəməsə",
        "pəməsəw",
        "the woman walks",
        "the-woman she.walks",
    ),
    (
        "ja.sentence.n1_the_child_walks",
        "ja.lexeme.hebrew_yeled_child",
        "ja.lexeme.munsee_pemsii_walk",
        "pəməsə",
        "pəməsəw",
        "the child walks",
        "the-child they.walk",
    ),
    (
        "ja.sentence.n1_the_man_walks",
        "ja.lexeme.munsee_lunew_man",
        "ja.lexeme.munsee_pemsii_walk",
        "pəməsə",
        "pəməsəw",
        "the man walks",
        "the-man he.walks",
    ),
    (
        "ja.sentence.n1_the_woman_is_good",
        "ja.lexeme.hebrew_ishah_woman",
        "ja.lexeme.munsee_welesii_good",
        "wələsə",
        "wələsəw",
        "the woman is good",
        "the-woman she.is-good",
    ),
]


def _load_records(data: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(data.glob("*.jsonl")):
        if path == OUTPUT:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            record = json.loads(line)
            if record["id"] in records:
                raise ValueError(f"duplicate dependency ID {record['id']}")
            records[record["id"]] = record
    return records


def _component(
    records: dict[str, dict[str, Any]],
    record_id: str,
    order: int,
    role: str,
    realization: str | None = None,
) -> dict[str, Any]:
    record = records[record_id]
    return {
        "order": order,
        "record_id": record_id,
        "record_revision": record["revision"],
        "sense_id": record["senses"][0]["id"],
        "role": role,
        "realization": realization
        if realization is not None
        else record["forms"]["judeo_algonquin"]["romanization"].strip("-"),
    }


def _orthography(romanization: str) -> dict[str, str]:
    return {
        "status": "componentwise",
        "profile_id": COMPONENTWISE_PROFILE,
        "script_origin": "componentwise",
        "input_system": "revision_pinned_components",
        "input_level": "componentwise",
        "source_exact": "",
        "normalized_input": romanization,
        "reversibility": "componentwise",
    }


def _record(
    records: dict[str, dict[str, Any]],
    *,
    record_id: str,
    record_type: str,
    english: str,
    hebrew: str,
    romanization: str,
    literal: str,
    definition: str,
    part_of_speech: str,
    components: list[dict[str, Any]],
    constructions: list[str],
    operation: str,
    domains: list[str],
    segmentation: str | None = None,
    morpheme_gloss: str | None = None,
) -> dict[str, Any]:
    dependencies = list(
        dict.fromkeys(
            [component["record_id"] for component in components] + constructions
        )
    )
    dependency_revisions = {
        dependency: records[dependency]["revision"] for dependency in dependencies
    }
    sense_id = f"{record_id}.sense.regression"
    revised = record_id in POST_EMBEDDING_REVISED
    return {
        "schema_version": 1,
        "id": record_id,
        "record_type": record_type,
        "revision": 3 if revised else 2,
        "status": "candidate",
        "level": "N1",
        "forms": {
            "english": [english],
            "judeo_algonquin": {
                "hebrew_script": unicodedata.normalize("NFC", hebrew),
                "romanization": romanization,
                "segmentation": segmentation or romanization.replace(" ", "-"),
                "morpheme_gloss": morpheme_gloss or literal,
                "orthography": _orthography(romanization),
            },
        },
        "senses": [
            {
                "id": sense_id,
                "glosses": [english],
                "definition": definition,
                "part_of_speech": part_of_speech,
                "translations": {
                    "literal": [literal],
                    "idiomatic": [english.capitalize() + ("." if record_type == "sentence" else "")],
                },
            }
        ],
        "grammatical_features": [
            "Every component and construction is revision-pinned.",
            "This record tests an already declared N1 construction and adds no productive rule.",
        ],
        "notes": {
            "translation": ["The English rendering is deliberately limited to the tested sense."],
            "grammar": ["A failing dependency or construction revision invalidates this record."],
            "design": [
                "The composition tests co-parent interaction without presenting the result as inherited history."
            ],
        },
        "formation": {
            "historical_etymology": [],
            "formation_kind": "mixed" if record_type == "sentence" else "compound",
            "inputs": [
                {
                    "input_type": "language_record",
                    "input_id": dependency,
                    "form": "",
                    "contribution": "Revision-pinned component or construction in this regression.",
                }
                for dependency in dependencies
            ],
            "operations": [
                {
                    "order": 1,
                    "operation": operation,
                    "description": "Apply only the declared revision-pinned construction to the listed components.",
                }
            ],
            "formation_process": "Deterministic composition from reviewed candidate dependencies.",
            "design_alignment": (
                "Exercises ordinary same-parent and cross-parent combinations before the wider phrase and sentence epochs."
            ),
        },
        "source_evidence": [],
        "provenance": {
            "creator_type": "model",
            "source_ids": [],
            "generation_note": (
                "Rendered deterministically from a frozen regression template; no generative-model API call was used."
            ),
        },
        "relations": {
            "depends_on": dependencies,
            "related_to": [],
            "conflicts_with": [],
            "supersedes": [],
            "superseded_by": [],
            "dependency_revisions": dependency_revisions,
        },
        "composition": {"components": components, "construction_ids": constructions},
        "construction_spec": None,
        "paradigm": None,
        "metadata": {
            "registers": ["ordinary"],
            "domains": domains,
            "tags": [
                "n1-core",
                "candidate",
                "noncanonical",
                "composed",
                "regression",
                "componentwise-orthography",
            ],
            "creative_anchor": None,
        },
        "created_at": CREATED_AT,
        "updated_at": DONOR_REFRESHED_AT,
        "change_note": (
            "Refreshed dependency revisions after the source-facing lexical layer was "
            "classified as donor evidence."
        ),
    }


def _hebrew(records: dict[str, dict[str, Any]], record_id: str) -> str:
    return records[record_id]["forms"]["judeo_algonquin"]["hebrew_script"]


def _roman(records: dict[str, dict[str, Any]], record_id: str) -> str:
    return records[record_id]["forms"]["judeo_algonquin"]["romanization"].strip("-")


def render(data: Path = DATA) -> list[dict[str, Any]]:
    records = _load_records(data)
    output: list[dict[str, Any]] = []

    for record_id, first_id, second_id, english in COORDINATIONS:
        first_roman, second_roman = _roman(records, first_id), _roman(records, second_id)
        roman = f"{first_roman} wə-{second_roman}"
        components = [
            _component(records, first_id, 1, "first conjunct"),
            _component(records, COORDINATOR, 2, "coordinator", "wə"),
            _component(records, second_id, 3, "second conjunct"),
        ]
        output.append(
            _record(
                records,
                record_id=record_id,
                record_type="phrase",
                english=english,
                hebrew=f"{_hebrew(records, first_id)} וְ{_hebrew(records, second_id)}",
                romanization=roman,
                literal=english.replace(" and ", "-and-"),
                definition=f"A coordinated phrase naming {english}.",
                part_of_speech="coordinate noun phrase",
                components=components,
                constructions=[COORDINATION],
                operation="combine",
                domains=["ordinary-life", "coordination"],
            )
        )

    for record_id, host_id, english in DEFINITES:
        host_roman = _roman(records, host_id)
        roman = f"ha-{host_roman}"
        components = [
            _component(records, ARTICLE, 1, "definite marker", "ha"),
            _component(records, host_id, 2, "definite host"),
        ]
        output.append(
            _record(
                records,
                record_id=record_id,
                record_type="phrase",
                english=english,
                hebrew=f"הַ{_hebrew(records, host_id)}",
                romanization=roman,
                literal=f"DEF-{english.removeprefix('the ')}",
                definition=f"A definite nominal phrase meaning {english}.",
                part_of_speech="definite noun phrase",
                components=components,
                constructions=[DEFINITE],
                operation="combine",
                domains=["people", "reference", "ordinary-life"],
            )
        )

    for record_id, host_id, english in PLURALS:
        host_roman = _roman(records, host_id)
        roman = f"{host_roman}-al"
        components = [
            _component(records, host_id, 1, "inanimate-class pilot stem"),
            _component(records, PLURAL_INANIMATE, 2, "plural marker", "al"),
        ]
        output.append(
            _record(
                records,
                record_id=record_id,
                record_type="phrase",
                english=english,
                hebrew=f"{_hebrew(records, host_id)}־אַל",
                romanization=roman,
                literal=f"{english.rstrip('s')}-PL.IN",
                definition=f"A class-sensitive plural regression meaning {english}.",
                part_of_speech="inflected nominal phrase",
                components=components,
                constructions=[CLASS_PLURAL],
                operation="derive",
                domains=["home", "number", "ordinary-life"],
            )
        )

    for (
        record_id,
        subject_id,
        predicate_id,
        stem_realization,
        predicate_surface,
        english,
        literal,
    ) in SENTENCES:
        subject_roman = _roman(records, subject_id)
        roman = f"ha-{subject_roman} {predicate_surface}"
        components = [
            _component(records, ARTICLE, 1, "definite marker", "ha"),
            _component(records, subject_id, 2, "subject"),
            _component(records, predicate_id, 3, "predicate stem", stem_realization),
            _component(records, THIRD, 4, "predicate person", "w"),
        ]
        output.append(
            _record(
                records,
                record_id=record_id,
                record_type="sentence",
                english=english,
                hebrew=f"הַ{_hebrew(records, subject_id)} {encode_munsee_transport(predicate_surface)}",
                romanization=roman,
                literal=literal,
                definition=f"A bounded contact-clause regression meaning {english}.",
                part_of_speech="intransitive clause",
                components=components,
                constructions=[DEFINITE, AI_THIRD, CONTACT_CLAUSE],
                operation="combine",
                domains=["people", "predication", "ordinary-life"],
                segmentation=(
                    f"ha-{subject_roman}-"
                    + ("pəməsii" if predicate_id.endswith("pemsii_walk") else "wələsii")
                    + "-w"
                ),
                morpheme_gloss=(
                    "DEF-subject-walk-3"
                    if predicate_id.endswith("pemsii_walk")
                    else "DEF-subject-be_good-3"
                ),
            )
        )

    ids = [record["id"] for record in output]
    if len(output) != 12 or len(set(ids)) != len(ids):
        raise ValueError("regression renderer must produce exactly 12 unique records")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    rendered = render(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            for record in rendered
        ),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "records": len(rendered)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
