"""Deterministic composition checks that go beyond structural validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Sequence

from .store import cosine_similarity


COORDINATION = "ja.construction.n1_nominal_coordination"
DEFINITE = "ja.construction.n1_definite_prefix"
CLASS_PLURAL = "ja.construction.n1_class_plural"
AI_THIRD = "ja.construction.n1_ai_third_predicate"
CONTACT_CLAUSE = "ja.construction.n1_contact_subject_predicate"
EXPECTED_PILOT_CONSTRUCTIONS = {
    "ja.phrase.n1_bread_and_water": {COORDINATION},
    "ja.phrase.n1_houses": {CLASS_PLURAL},
    "ja.sentence.n1_the_man_is_good": {DEFINITE, AI_THIRD, CONTACT_CLAUSE},
    "ja.phrase.n1_mother_and_father": {COORDINATION},
    "ja.phrase.n1_woman_and_child": {COORDINATION},
    "ja.phrase.n1_bread_and_milk": {COORDINATION},
    "ja.phrase.n1_fruit_and_water": {COORDINATION},
    "ja.phrase.n1_the_woman": {DEFINITE},
    "ja.phrase.n1_the_child": {DEFINITE},
    "ja.phrase.n1_doors": {CLASS_PLURAL},
    "ja.phrase.n1_chairs": {CLASS_PLURAL},
    "ja.sentence.n1_the_woman_walks": {DEFINITE, AI_THIRD, CONTACT_CLAUSE},
    "ja.sentence.n1_the_child_walks": {DEFINITE, AI_THIRD, CONTACT_CLAUSE},
    "ja.sentence.n1_the_man_walks": {DEFINITE, AI_THIRD, CONTACT_CLAUSE},
    "ja.sentence.n1_the_woman_is_good": {DEFINITE, AI_THIRD, CONTACT_CLAUSE},
    "ja.phrase.perception_light_and_sound": {COORDINATION},
}

ANCHOR_AI_FIRST_PLURAL = "ja.construction.contact_ai_first_plural"
ANCHOR_GOODWILL_FRAME = "ja.construction.contact_goodwill_manner_frame"
ANCHOR_CELL_FORMS = {
    ("walk", "inclusive"): "kəpəməsiihna",
    ("walk", "exclusive"): "nəpəməsiihna",
    ("be-good", "inclusive"): "kəwələsiihna",
    ("be-good", "exclusive"): "nəwələsiihna",
    ("sing", "inclusive"): "kənaxkoohəmaahna",
    ("sing", "exclusive"): "nənaxkoohəmaahna",
}
ANCHOR_SENTENCE_CONTRACTS = {
    "ja.sentence.anchor_we_walk_inclusive": {
        "predicate": "walk",
        "stem_id": "ja.lexeme.contact_walk_ai",
        "constructions": {ANCHOR_AI_FIRST_PLURAL},
        "surface": "kəpəməsiihna",
        "frame": False,
    },
    "ja.sentence.anchor_we_sing_inclusive": {
        "predicate": "sing",
        "stem_id": "ja.lexeme.contact_sing_ai",
        "constructions": {ANCHOR_AI_FIRST_PLURAL},
        "surface": "kənaxkoohəmaahna",
        "frame": False,
    },
    "ja.sentence.anchor_we_walk_with_goodwill": {
        "predicate": "walk",
        "stem_id": "ja.lexeme.contact_walk_ai",
        "constructions": {ANCHOR_AI_FIRST_PLURAL, ANCHOR_GOODWILL_FRAME},
        "surface": "wəlew kəpəməsiihna",
        "frame": True,
    },
}

PERCEPTION_ABSOLUTE = "ja.construction.contact_perception_absolute_first_plural"
FINITE_COORDINATION = "ja.construction.contact_finite_coordination"
PERCEPTION_NOMINAL_PHRASE = "ja.phrase.perception_light_and_sound"
PERCEPTION_CELL_FORMS = {
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
PERCEPTION_STEMS = {
    "ja.lexeme.contact_see_animate": ("see", "animate", "neew"),
    "ja.lexeme.contact_see_inanimate": ("see", "inanimate", "neem"),
    "ja.lexeme.contact_hear_animate": ("hear", "animate", "pəntaw"),
    "ja.lexeme.contact_hear_inanimate": ("hear", "inanimate", "pəntam"),
    "ja.lexeme.contact_look_animate": ("look-at", "animate", "pənaw"),
    "ja.lexeme.contact_look_inanimate": ("look-at", "inanimate", "pənam"),
}
PERCEPTION_OBJECTS = {
    "ja.lexeme.contact_person": ("animate", "adam"),
    "ja.lexeme.contact_light": ("inanimate", "or"),
    "ja.lexeme.contact_sound": ("inanimate", "kol"),
    "ja.lexeme.contact_road": ("inanimate", "aanay"),
}
PERCEPTION_SENTENCE_CONTRACTS = {
    "ja.sentence.perception_we_see_light": (
        "ja.lexeme.contact_see_inanimate",
        "ja.lexeme.contact_light",
        "kəneemohna or",
    ),
    "ja.sentence.perception_we_see_person": (
        "ja.lexeme.contact_see_animate",
        "ja.lexeme.contact_person",
        "kəneewahna adam",
    ),
    "ja.sentence.perception_we_hear_sound": (
        "ja.lexeme.contact_hear_inanimate",
        "ja.lexeme.contact_sound",
        "kəpəntamohna kol",
    ),
    "ja.sentence.perception_we_hear_person": (
        "ja.lexeme.contact_hear_animate",
        "ja.lexeme.contact_person",
        "kəpəntawahna adam",
    ),
    "ja.sentence.perception_we_look_road": (
        "ja.lexeme.contact_look_inanimate",
        "ja.lexeme.contact_road",
        "kəpənamohna aanay",
    ),
    "ja.sentence.perception_we_look_person": (
        "ja.lexeme.contact_look_animate",
        "ja.lexeme.contact_person",
        "kəpənawahna adam",
    ),
}
FINITE_COORDINATION_CONTRACTS = {
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
NARRATIVE_FIREWALL_TAGS = {
    "narrative",
    "wayyiqtol-derived",
    "weqatal-derived",
    "foreground-chain",
}
NARRATIVE_SEMANTIC_PATTERNS = (
    r"\bthen\b",
    r"\btherefore\b",
    r"\bsequence\w*\b",
    r"\bforeground\w*\b",
    r"\bwayyiqtol\b",
    r"\bweqatal\b",
)


def _components(record: dict[str, Any]) -> list[dict[str, Any]]:
    composition = record.get("composition")
    if not isinstance(composition, dict):
        return []
    return [item for item in composition.get("components", []) if isinstance(item, dict)]


def _constructions(record: dict[str, Any]) -> set[str]:
    composition = record.get("composition")
    if not isinstance(composition, dict):
        return set()
    return {
        item for item in composition.get("construction_ids", []) if isinstance(item, str)
    }


def evaluate_pilot_compositions(records: Sequence[dict[str, Any]]) -> list[str]:
    """Return explainable violations of the bounded N1 construction contracts."""

    records_by_id = {
        record["id"]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    findings: list[str] = []

    for record in records:
        record_id = record.get("id", "<unknown>")
        components = _components(record)
        construction_ids = _constructions(record)
        roles = [component.get("role") for component in components]

        expected_constructions = EXPECTED_PILOT_CONSTRUCTIONS.get(str(record_id))
        if expected_constructions is not None and construction_ids != expected_constructions:
            missing = sorted(expected_constructions - construction_ids)
            unexpected = sorted(construction_ids - expected_constructions)
            findings.append(
                f"{record_id}: pilot construction declaration mismatch; "
                f"missing={missing!r}, unexpected={unexpected!r}"
            )

        if COORDINATION in construction_ids:
            expected = ["first conjunct", "coordinator", "second conjunct"]
            if roles != expected:
                findings.append(
                    f"{record_id}: nominal coordination roles must be {expected!r}"
                )
            elif components[1].get("record_id") != "ja.morpheme.hebrew_coord_we":
                findings.append(
                    f"{record_id}: the pilot coordinator slot must use the coordinator morpheme"
                )
            elif components[1].get("realization") != "wə":
                findings.append(f"{record_id}: pilot coordinator must realize as wə")

        if CLASS_PLURAL in construction_ids:
            if len(components) != 2:
                findings.append(
                    f"{record_id}: class plural requires one stem and one suffix component"
                )
            else:
                stem = records_by_id.get(str(components[0].get("record_id")), {})
                tags = stem.get("metadata", {}).get("tags", []) if stem else []
                suffix_id = components[1].get("record_id")
                expected_suffix = None
                if "pilot-class:animate" in tags:
                    expected_suffix = "ja.morpheme.munsee_plural_ak"
                elif "pilot-class:inanimate" in tags:
                    expected_suffix = "ja.morpheme.munsee_plural_al"
                else:
                    findings.append(
                        f"{record_id}: class plural host lacks an explicit pilot class"
                    )
                if expected_suffix is not None and suffix_id != expected_suffix:
                    findings.append(
                        f"{record_id}: suffix {suffix_id} conflicts with the host's pilot class"
                    )
                expected_realization = {
                    "ja.morpheme.munsee_plural_ak": "ak",
                    "ja.morpheme.munsee_plural_al": "al",
                }.get(str(suffix_id))
                if (
                    expected_realization is not None
                    and components[1].get("realization") != expected_realization
                ):
                    findings.append(
                        f"{record_id}: plural suffix realization must be {expected_realization}"
                    )

        if DEFINITE in construction_ids:
            host = (
                records_by_id.get(str(components[1].get("record_id")), {})
                if len(components) >= 2
                else {}
            )
            if (
                len(components) < 2
                or components[0].get("record_id") != "ja.morpheme.hebrew_definite_ha"
                or components[0].get("realization") != "ha"
                or host.get("record_type") not in {"lexeme", "phrase"}
            ):
                findings.append(
                    f"{record_id}: definite ha- must immediately precede a nominal host"
                )

        if AI_THIRD in construction_ids:
            predicate_positions = [
                index for index, role in enumerate(roles) if role == "predicate stem"
            ]
            if len(predicate_positions) != 1:
                findings.append(
                    f"{record_id}: AI third construction requires one predicate stem"
                )
            else:
                position = predicate_positions[0]
                predicate = records_by_id.get(
                    str(components[position].get("record_id")), {}
                )
                predicate_senses = predicate.get("senses", []) if predicate else []
                selected_sense = next(
                    (
                        sense
                        for sense in predicate_senses
                        if isinstance(sense, dict)
                        and sense.get("id") == components[position].get("sense_id")
                    ),
                    {},
                )
                if (
                    predicate.get("record_type") != "lexeme"
                    or selected_sense.get("part_of_speech")
                    != "animate intransitive verb stem"
                    or position + 1 >= len(components)
                    or components[position + 1].get("record_id")
                    != "ja.morpheme.munsee_third_w"
                    or components[position + 1].get("role") != "predicate person"
                    or components[position + 1].get("realization") != "w"
                ):
                    findings.append(
                        f"{record_id}: AI predicate stem must be followed by third-person -w"
                    )

        if CONTACT_CLAUSE in construction_ids:
            try:
                subject_position = roles.index("subject")
                predicate_position = roles.index("predicate stem")
            except ValueError:
                findings.append(
                    f"{record_id}: contact clause requires overt subject and predicate roles"
                )
            else:
                if subject_position >= predicate_position:
                    findings.append(
                        f"{record_id}: pilot contact clause requires subject before predicate"
                    )

    return findings


def evaluate_anchor_chorus_compositions(
    records: Sequence[dict[str, Any]],
) -> list[str]:
    """Enforce the bounded six-cell chorus paradigm and its three composed clauses."""

    records_by_id = {
        record["id"]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    findings: list[str] = []
    construction = records_by_id.get(ANCHOR_AI_FIRST_PLURAL)
    if construction is None:
        if any(record_id in records_by_id for record_id in ANCHOR_SENTENCE_CONTRACTS):
            findings.append(f"{ANCHOR_AI_FIRST_PLURAL}: required by chorus sentences")
        return findings

    spec = construction.get("construction_spec")
    if not isinstance(spec, dict) or spec.get("productivity") != "limited":
        findings.append(
            f"{ANCHOR_AI_FIRST_PLURAL}: the three-host candidate must remain limited"
        )
    paradigm = construction.get("paradigm")
    cells = paradigm.get("cells", []) if isinstance(paradigm, dict) else []
    actual_cells: dict[tuple[str, str], dict[str, Any]] = {}
    for cell in cells:
        if not isinstance(cell, dict) or not isinstance(cell.get("features"), dict):
            continue
        features = cell["features"]
        key = (str(features.get("predicate")), str(features.get("clusivity")))
        actual_cells[key] = cell
        gloss = str(cell.get("morpheme_gloss", ""))
        if "INCL" in gloss or "EXCL" in gloss or not gloss.startswith("PERS.PFX~"):
            findings.append(
                f"{ANCHOR_AI_FIRST_PLURAL}: {key!r} must not assign clusivity "
                "to an isolated prefix"
            )
        meaning = str(cell.get("meaning", ""))
        clusivity = key[1]
        if (
            clusivity == "inclusive"
            and ("including the addressee" not in meaning or "excluding" in meaning)
        ) or (
            clusivity == "exclusive"
            and ("excluding the addressee" not in meaning or "including" in meaning)
        ):
            findings.append(
                f"{ANCHOR_AI_FIRST_PLURAL}: {key!r} clusivity and meaning must agree"
            )
    if set(actual_cells) != set(ANCHOR_CELL_FORMS):
        findings.append(
            f"{ANCHOR_AI_FIRST_PLURAL}: paradigm must contain exactly the six licensed cells"
        )
    for key, expected_surface in ANCHOR_CELL_FORMS.items():
        cell = actual_cells.get(key)
        if cell is not None and cell.get("romanization") != expected_surface:
            findings.append(
                f"{ANCHOR_AI_FIRST_PLURAL}: {key!r} surface must be {expected_surface}"
            )

    for record_id, contract in ANCHOR_SENTENCE_CONTRACTS.items():
        sentence = records_by_id.get(record_id)
        if sentence is None:
            findings.append(f"{record_id}: required chorus composition is missing")
            continue
        constructions = _constructions(sentence)
        expected_constructions = contract["constructions"]
        if constructions != expected_constructions:
            findings.append(
                f"{record_id}: chorus construction declaration mismatch; "
                f"expected={sorted(expected_constructions)!r}, actual={sorted(constructions)!r}"
            )
        components = _components(sentence)
        stem_id = contract["stem_id"]
        stem_components = [item for item in components if item.get("record_id") == stem_id]
        if len(stem_components) != 1:
            findings.append(
                f"{record_id}: must contain exactly the licensed predicate stem {stem_id}"
            )
        surface = sentence.get("forms", {}).get("judeo_algonquin", {}).get("romanization")
        if surface != contract["surface"]:
            findings.append(
                f"{record_id}: inclusive chorus surface must be {contract['surface']}"
            )
        expected_cell = ANCHOR_CELL_FORMS[(str(contract["predicate"]), "inclusive")]
        if expected_cell not in str(surface):
            findings.append(
                f"{record_id}: selected predicate must realize the declared inclusive cell"
            )
        sense_text = " ".join(
            str(value)
            for sense in sentence.get("senses", [])
            if isinstance(sense, dict)
            for value in [
                sense.get("definition", ""),
                *sense.get("translations", {}).get("literal", []),
            ]
        )
        if "excluding" in sense_text or not (
            "includes the addressee" in sense_text or "including.you" in sense_text
        ):
            findings.append(
                f"{record_id}: inclusive surface and participant meaning must agree"
            )

        if contract["frame"]:
            frame_components = [
                item
                for item in components
                if item.get("record_id") == "ja.lexeme.contact_welew_goodwill"
            ]
            if (
                len(components) != 2
                or len(frame_components) != 1
                or components[0].get("record_id")
                != "ja.lexeme.contact_welew_goodwill"
                or components[0].get("realization") != "wəlew"
            ):
                findings.append(
                    f"{record_id}: wəlew must be the sole first goodwill-frame element"
                )
        elif any(
            item.get("record_id") == "ja.lexeme.contact_welew_goodwill"
            for item in components
        ):
            findings.append(f"{record_id}: unlicensed goodwill-frame element")

    return findings


def _positive_semantic_text(record: dict[str, Any]) -> str:
    """Collect asserted meanings while excluding notes that document rejected readings."""

    values: list[str] = []
    forms = record.get("forms")
    if isinstance(forms, dict):
        english = forms.get("english")
        if isinstance(english, list):
            values.extend(item for item in english if isinstance(item, str))
    senses = record.get("senses")
    if isinstance(senses, list):
        for sense in senses:
            if not isinstance(sense, dict):
                continue
            for key in ("glosses",):
                items = sense.get(key)
                if isinstance(items, list):
                    values.extend(item for item in items if isinstance(item, str))
            definition = sense.get("definition")
            if isinstance(definition, str):
                values.append(definition)
            translations = sense.get("translations")
            if isinstance(translations, dict):
                for items in translations.values():
                    if isinstance(items, list):
                        values.extend(item for item in items if isinstance(item, str))
    return " ".join(values).lower()


def _declared_clusivity(record: dict[str, Any]) -> str | None:
    tags = record.get("metadata", {}).get("tags", [])
    values = {
        item
        for item in tags
        if isinstance(item, str) and item in {"inclusive", "exclusive"}
    }
    return next(iter(values)) if len(values) == 1 else None


def _asserts_narrative_chain(value: str) -> bool:
    return any(re.search(pattern, value) for pattern in NARRATIVE_SEMANTIC_PATTERNS)


def evaluate_perception_compositions(
    records: Sequence[dict[str, Any]],
) -> list[str]:
    """Enforce the bounded perception Absolute and ordinary clause coordination."""

    records_by_id = {
        record["id"]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    tranche_markers = {
        PERCEPTION_ABSOLUTE,
        FINITE_COORDINATION,
        PERCEPTION_NOMINAL_PHRASE,
        *PERCEPTION_SENTENCE_CONTRACTS,
        *FINITE_COORDINATION_CONTRACTS,
    }
    if not tranche_markers.intersection(records_by_id):
        return []

    findings: list[str] = []

    phrase = records_by_id.get(PERCEPTION_NOMINAL_PHRASE)
    if phrase is None:
        findings.append(f"{PERCEPTION_NOMINAL_PHRASE}: required perception phrase is missing")
    else:
        components = _components(phrase)
        expected_phrase_components = [
            ("ja.lexeme.contact_light", "first conjunct", "or"),
            ("ja.morpheme.hebrew_coord_we", "coordinator", "wə"),
            ("ja.lexeme.contact_sound", "second conjunct", "kol"),
        ]
        actual_phrase_components = [
            (
                component.get("record_id"),
                component.get("role"),
                component.get("realization"),
            )
            for component in components
        ]
        surface = phrase.get("forms", {}).get("judeo_algonquin", {}).get(
            "romanization"
        )
        if (
            _constructions(phrase) != {COORDINATION}
            or actual_phrase_components != expected_phrase_components
            or surface != "or wə-kol"
        ):
            findings.append(
                f"{PERCEPTION_NOMINAL_PHRASE}: light and sound must retain proclitic wə- on the second conjunct"
            )

    construction = records_by_id.get(PERCEPTION_ABSOLUTE)
    if construction is None:
        findings.append(f"{PERCEPTION_ABSOLUTE}: required by perception sentences")
    else:
        spec = construction.get("construction_spec")
        if not isinstance(spec, dict) or spec.get("productivity") != "limited":
            findings.append(
                f"{PERCEPTION_ABSOLUTE}: the six-stem candidate must remain limited"
            )
        paradigm = construction.get("paradigm")
        cells = paradigm.get("cells", []) if isinstance(paradigm, dict) else []
        if len(cells) != len(PERCEPTION_CELL_FORMS):
            findings.append(
                f"{PERCEPTION_ABSOLUTE}: paradigm must contain exactly twelve cells"
            )
        actual_cells: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
        expected_feature_names = {
            "predicate",
            "object_class",
            "clusivity",
            "person",
            "number",
        }
        for cell in cells:
            if not isinstance(cell, dict) or not isinstance(cell.get("features"), dict):
                continue
            features = cell["features"]
            if set(features) != expected_feature_names:
                findings.append(
                    f"{PERCEPTION_ABSOLUTE}: every cell must declare exactly the five licensed features"
                )
                continue
            key = (
                str(features["predicate"]),
                str(features["object_class"]),
                str(features["clusivity"]),
                str(features["person"]),
                str(features["number"]),
            )
            if key in actual_cells:
                findings.append(f"{PERCEPTION_ABSOLUTE}: duplicate cell {key!r}")
            actual_cells[key] = cell
            if cell.get("status") != "adapted_candidate":
                findings.append(
                    f"{PERCEPTION_ABSOLUTE}: {key!r} must remain an adapted candidate"
                )
            gloss = str(cell.get("morpheme_gloss", ""))
            if "INCL" in gloss or "EXCL" in gloss or not gloss.startswith("PERS.PFX~"):
                findings.append(
                    f"{PERCEPTION_ABSOLUTE}: {key!r} must not assign clusivity to an isolated prefix"
                )
            meaning = str(cell.get("meaning", ""))
            if (
                key[2] == "inclusive"
                and ("including the addressee" not in meaning or "excluding" in meaning)
            ) or (
                key[2] == "exclusive"
                and ("excluding the addressee" not in meaning or "including" in meaning)
            ):
                findings.append(
                    f"{PERCEPTION_ABSOLUTE}: {key!r} clusivity and meaning must agree"
                )
        if set(actual_cells) != set(PERCEPTION_CELL_FORMS):
            findings.append(
                f"{PERCEPTION_ABSOLUTE}: paradigm contains an unlicensed or missing feature bundle"
            )
        for key, expected_surface in PERCEPTION_CELL_FORMS.items():
            cell = actual_cells.get(key)
            if cell is not None and cell.get("romanization") != expected_surface:
                findings.append(
                    f"{PERCEPTION_ABSOLUTE}: {key!r} surface must be {expected_surface}"
                )

    for record_id, (stem_id, object_id, expected_surface) in (
        PERCEPTION_SENTENCE_CONTRACTS.items()
    ):
        sentence = records_by_id.get(record_id)
        if sentence is None:
            findings.append(f"{record_id}: required perception composition is missing")
            continue
        if _constructions(sentence) != {PERCEPTION_ABSOLUTE}:
            findings.append(
                f"{record_id}: must declare exactly the limited perception Absolute"
            )
        components = _components(sentence)
        if len(components) != 2:
            findings.append(
                f"{record_id}: perception Absolute requires predicate then one overt object"
            )
            continue
        stem_spec = PERCEPTION_STEMS.get(str(components[0].get("record_id")))
        object_spec = PERCEPTION_OBJECTS.get(str(components[1].get("record_id")))
        expected_stem_spec = PERCEPTION_STEMS[stem_id]
        expected_object_spec = PERCEPTION_OBJECTS[object_id]
        if (
            components[0].get("record_id") != stem_id
            or components[0].get("role") != "predicate stem"
            or components[0].get("realization") != expected_stem_spec[2]
            or components[1].get("record_id") != object_id
            or components[1].get("role")
            != f"indefinite {expected_object_spec[0]} object"
            or components[1].get("realization") != expected_object_spec[1]
        ):
            findings.append(
                f"{record_id}: predicate/object identities, order, roles, or realizations violate its contract"
            )
        if stem_spec is None or object_spec is None or stem_spec[1] != object_spec[0]:
            findings.append(
                f"{record_id}: TA/TI predicate class conflicts with the overt object's admitted class"
            )
        actual_surface = sentence.get("forms", {}).get("judeo_algonquin", {}).get(
            "romanization"
        )
        if actual_surface != expected_surface:
            findings.append(
                f"{record_id}: inclusive perception surface must be {expected_surface}"
            )
        tags = sentence.get("metadata", {}).get("tags", [])
        expected_class_tag = f"object-class:{expected_object_spec[0]}"
        declared_class_tags = {
            tag
            for tag in tags
            if isinstance(tag, str) and tag.startswith("object-class:")
        }
        if (
            _declared_clusivity(sentence) != "inclusive"
            or declared_class_tags != {expected_class_tag}
        ):
            findings.append(
                f"{record_id}: structured clusivity and object-class tags must match the clause"
            )

    hear_records = {
        "ja.lexeme.contact_hear_animate",
        "ja.lexeme.contact_hear_inanimate",
        "ja.sentence.perception_we_hear_sound",
        "ja.sentence.perception_we_hear_person",
        *FINITE_COORDINATION_CONTRACTS,
    }
    for record_id in hear_records:
        record = records_by_id.get(record_id)
        if record is not None and "listen" in _positive_semantic_text(record):
            findings.append(
                f"{record_id}: positive semantics may claim literal hear, not listen"
            )

    finite = records_by_id.get(FINITE_COORDINATION)
    if finite is None:
        findings.append(f"{FINITE_COORDINATION}: required by coordinated sentences")
    else:
        spec = finite.get("construction_spec")
        tags = finite.get("metadata", {}).get("tags", [])
        registers = finite.get("metadata", {}).get("registers", [])
        if not isinstance(spec, dict) or spec.get("productivity") != "limited":
            findings.append(f"{FINITE_COORDINATION}: must remain limited")
        elif "wə-CLAUSE₂" not in str(spec.get("formalism", "")):
            findings.append(
                f"{FINITE_COORDINATION}: must preserve proclitic wə- on the second clause"
            )
        if "narrative-firewall" not in tags:
            findings.append(
                f"{FINITE_COORDINATION}: ordinary coordination requires its narrative firewall"
            )
        if "narrative" in registers or NARRATIVE_FIREWALL_TAGS.intersection(tags):
            findings.append(
                f"{FINITE_COORDINATION}: ordinary coordination cannot enter the narrative register"
            )

    if finite is not None:
        finite_semantic_text = _positive_semantic_text(finite)
        if _asserts_narrative_chain(finite_semantic_text):
            findings.append(
                f"{FINITE_COORDINATION}: positive semantics cannot assert narrative-chain behavior"
            )
    for record_id, (first_id, second_id, expected_surface) in (
        FINITE_COORDINATION_CONTRACTS.items()
    ):
        sentence = records_by_id.get(record_id)
        if sentence is None:
            findings.append(f"{record_id}: required finite coordination is missing")
            continue
        if _constructions(sentence) != {FINITE_COORDINATION}:
            findings.append(
                f"{record_id}: must declare exactly ordinary finite coordination"
            )
        components = _components(sentence)
        expected_roles = ["first clause", "coordinator", "second clause"]
        if len(components) != 3 or [item.get("role") for item in components] != expected_roles:
            findings.append(
                f"{record_id}: finite coordination roles must be {expected_roles!r}"
            )
            continue
        first = records_by_id.get(str(components[0].get("record_id")))
        second = records_by_id.get(str(components[2].get("record_id")))
        if (
            components[0].get("record_id") != first_id
            or components[1].get("record_id") != "ja.morpheme.hebrew_coord_we"
            or components[1].get("realization") != "wə"
            or components[2].get("record_id") != second_id
        ):
            findings.append(
                f"{record_id}: clause identities, hearing-first order, or coordinator violate its contract"
            )
        for position, host in ((0, first), (2, second)):
            host_surface = (
                host.get("forms", {}).get("judeo_algonquin", {}).get("romanization")
                if isinstance(host, dict)
                else None
            )
            host_tags = host.get("metadata", {}).get("tags", []) if isinstance(host, dict) else []
            if (
                not isinstance(host, dict)
                or host.get("record_type") != "sentence"
                or "contact-clause" not in host_tags
                or components[position].get("realization") != host_surface
            ):
                findings.append(
                    f"{record_id}: each conjunct must realize its referenced complete contact sentence"
                )
        first_clusivity = _declared_clusivity(first) if isinstance(first, dict) else None
        second_clusivity = _declared_clusivity(second) if isinstance(second, dict) else None
        if first_clusivity is None or second_clusivity is None or first_clusivity != second_clusivity:
            findings.append(
                f"{record_id}: coordinated clauses must declare matching clusivity"
            )
        joined_surface = (
            f"{components[0].get('realization', '')} "
            f"{components[1].get('realization', '')}-{components[2].get('realization', '')}"
        )
        actual_surface = sentence.get("forms", {}).get("judeo_algonquin", {}).get(
            "romanization"
        )
        if actual_surface != expected_surface or actual_surface != joined_surface:
            findings.append(
                f"{record_id}: surface must exactly join its two clauses with wə"
            )
        registers = sentence.get("metadata", {}).get("registers", [])
        sentence_tags = sentence.get("metadata", {}).get("tags", [])
        semantic_text = _positive_semantic_text(sentence)
        if (
            "narrative" in registers
            or NARRATIVE_FIREWALL_TAGS.intersection(sentence_tags)
            or _asserts_narrative_chain(semantic_text)
        ):
            findings.append(
                f"{record_id}: ordinary wə- may not assert narrative-chain semantics"
            )

    return findings


def load_semantic_queries(path: str | Path) -> list[dict[str, str]]:
    """Load a frozen retrieval set with enough metadata to explain each target."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path}: expected a non-empty JSON array")
    required = {"id", "query", "expected_id", "rationale"}
    queries: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError(f"{path}: query {index} must contain exactly {sorted(required)}")
        if any(not isinstance(item[key], str) or not item[key].strip() for key in required):
            raise ValueError(f"{path}: query {index} fields must be non-empty strings")
        if item["id"] in seen:
            raise ValueError(f"{path}: duplicate query id {item['id']}")
        seen.add(item["id"])
        queries.append(dict(item))
    return queries


def evaluate_semantic_rankings(
    record_ids: Sequence[str],
    record_vectors: Sequence[Sequence[float]],
    queries: Sequence[dict[str, str]],
    query_vectors: Sequence[Sequence[float]],
) -> dict[str, Any]:
    """Compute reproducible recall and ranking details from one vector batch."""

    if len(record_ids) != len(record_vectors):
        raise ValueError("record ids and vectors must have equal length")
    if len(queries) != len(query_vectors):
        raise ValueError("queries and vectors must have equal length")
    if not record_ids or not queries or len(set(record_ids)) != len(record_ids):
        raise ValueError("evaluation requires unique records and at least one query")
    known = set(record_ids)
    details: list[dict[str, Any]] = []
    for query, query_vector in zip(queries, query_vectors):
        expected_id = query["expected_id"]
        if expected_id not in known:
            raise ValueError(f"query {query['id']} expects unknown record {expected_id}")
        ranking = sorted(
            (
                {
                    "id": record_id,
                    "score": cosine_similarity(query_vector, record_vector),
                }
                for record_id, record_vector in zip(record_ids, record_vectors)
            ),
            key=lambda item: (-item["score"], item["id"]),
        )
        expected_rank = next(
            index for index, item in enumerate(ranking, start=1) if item["id"] == expected_id
        )
        details.append(
            {
                **query,
                "expected_rank": expected_rank,
                "reciprocal_rank": 1.0 / expected_rank,
                "top_3": ranking[:3],
                "ranking": ranking,
            }
        )
    count = len(details)
    return {
        "query_count": count,
        "recall_at_1": sum(item["expected_rank"] <= 1 for item in details) / count,
        "recall_at_3": sum(item["expected_rank"] <= 3 for item in details) / count,
        "mean_reciprocal_rank": sum(item["reciprocal_rank"] for item in details) / count,
        "queries": details,
    }
