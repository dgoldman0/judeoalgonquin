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
CONTACT_COORDINATOR = "ja.morpheme.contact_coord_we"
CONTACT_NOMINAL_COORDINATION = "ja.construction.contact_nominal_coordination"
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
TAM_OBVIATION_TAGS = {
    "past",
    "future",
    "perfective",
    "imperfective",
    "habitual",
    "proximate",
    "obviative",
}
NARRATIVE_SEMANTIC_PATTERNS = (
    r"\bthen\b",
    r"\btherefore\b",
    r"\bsequence\w*\b",
    r"\bforeground\w*\b",
    r"\bwayyiqtol\b",
    r"\bweqatal\b",
)
TAM_OBVIATION_SEMANTIC_PATTERNS = (
    r"\bwill\b",
    r"\bshall\b",
    r"\bgoing to\b",
    r"\bused to\b",
    r"\bhabitual\w*\b",
    r"\brepeatedly\b",
    r"\bperfective\b",
    r"\bimperfective\b",
    r"\b(?:past|present|future) tense\b",
    r"\bproximate\b",
    r"\bobviative\b",
)

SOURCE_STATIC_LOCATIVE = "ja.construction.munsee_static_locative_examples"
SOURCE_AI_PERSON = "ja.construction.munsee_ai_independent_person_number"
CONTACT_STATIC_LOCATIVE = "ja.construction.contact_static_locative"
CONTACT_POSTURE_AI = "ja.construction.contact_ai_posture_independent"
CONTACT_STATIC_CLAUSE = "ja.construction.contact_static_location_clause"
CONTACT_STATIC_WHERE = "ja.construction.contact_static_where_question"
CONTACT_WHERE = "ja.lexeme.contact_where"
CONTACT_LOCATIVE_MORPHEME = "ja.morpheme.contact_locative_enk"

SOURCE_RECORD_CONTRACTS = {
    "ja.morpheme.munsee_locative_enk": (
        "-ənk",
        "ənk",
        "LOC",
        "donor_candidate",
        "O'Meara 1990, p. 49, R19–R20",
        "/aanay-ənk/; /mohkaməy-ənk/",
    ),
    SOURCE_STATIC_LOCATIVE: (
        "HOST-ənk",
        "host-locative",
        "N-LOC",
        None,
        "O'Meara 1990, p. 49, R19–R20",
        "/aanay-ənk/ → aaneenk; /mohkaməy-ənk/ → mohkamiink",
    ),
    "ja.lexeme.munsee_apii_be_there": (
        "apii-",
        "apii",
        "be.there",
        "donor_candidate",
        "O'Meara 1990, p. 14, §1.3.2.4, example 1.10a",
        "apəw; /apii-w/",
    ),
    "ja.lexeme.munsee_lematapii_sit": (
        "ləmatapii-",
        "ləmatapii",
        "sit",
        "donor_candidate",
        "O'Meara 1990, p. 47, R13",
        "ləmatapəw /ləmatapii-w/; kələmatapiim /kə-ləmatapii-m/",
    ),
    "ja.lexeme.munsee_niipawii_stand": (
        "niipaw-ii-",
        "niipaw-ii",
        "stand-AF",
        "donor_candidate",
        "O'Meara 1990, p. 133, §2.4.2.2, example 2.83a",
        "niipawəw; /niipaw-ii-w/",
    ),
    SOURCE_AI_PERSON: (
        "AFFIX-AI-STEM-AFFIX",
        "person-AI-person.number",
        "PERS-AI-PERS.NUM",
        None,
        "O'Meara 1990, p. 86, §2.2.0, example 2.37 and footnotes 24–25",
        "/nə-/…/-m/; /kə-/…/-m/; …/-w/; /kə-/…/-hna/; /nə-/…/-hna/; /kə-/…/-hmwa/; …/-w-ak/",
    ),
}
SOURCE_LOCATIVE_CELLS = {
    "road": (
        "aaneenk",
        "aanay-ənk",
        "road-LOC",
        "on the road",
        "attested_source",
    ),
    "ice": (
        "mohkamiink",
        "mohkaməy-ənk",
        "ice-LOC",
        "on the ice",
        "attested_source",
    ),
}
SOURCE_AI_CELLS = {
    ("first", "singular", "not_applicable"): (
        "nə-STEM-m", "nə-STEM-m", "1-AI-1SG", "I do or am the AI predicate"
    ),
    ("second", "singular", "not_applicable"): (
        "kə-STEM-m", "kə-STEM-m", "2-AI-2SG", "you singular do or are the AI predicate"
    ),
    ("third", "singular", "not_applicable"): (
        "STEM-w", "STEM-w", "AI-3", "a third person does or is the AI predicate"
    ),
    ("first", "plural", "inclusive"): (
        "kə-STEM-hna", "kə-STEM-hna", "1-AI-1PL",
        "we, including the addressee, do or are the AI predicate",
    ),
    ("first", "plural", "exclusive"): (
        "nə-STEM-hna", "nə-STEM-hna", "1-AI-1PL",
        "we, excluding the addressee, do or are the AI predicate",
    ),
    ("second", "plural", "not_applicable"): (
        "kə-STEM-hmwa", "kə-STEM-hmwa", "2-AI-2PL",
        "you plural do or are the AI predicate",
    ),
    ("third", "plural", "not_applicable"): (
        "STEM-w-ak", "STEM-w-ak", "AI-3-PL",
        "third persons do or are the AI predicate",
    ),
}
CONTACT_LOCATIVE_CELLS = {
    "road": ("ja.lexeme.contact_road", "ja.phrase.static_on_road", "aaneenk"),
    "ice": ("ja.lexeme.contact_ice", "ja.phrase.static_on_ice", "mohkamiink"),
    "bed": ("ja.lexeme.contact_bed", "ja.phrase.static_at_bed", "apiineenk"),
    "house": ("ja.lexeme.contact_house", "ja.phrase.static_in_house", "bayitənk"),
    "room": ("ja.lexeme.contact_room", "ja.phrase.static_in_room", "xederənk"),
    "table": ("ja.lexeme.contact_table", "ja.phrase.static_at_table", "šulxanənk"),
}
POSTURE_STEMS = {
    "ja.lexeme.contact_be_there_ai": ("be_located", "apii"),
    "ja.lexeme.contact_sit_ai": ("sit", "ləmatapii"),
    "ja.lexeme.contact_stand_ai": ("stand", "niipawii"),
}
CONTACT_ATOMIC_CONTRACTS = {
    CONTACT_COORDINATOR: ("wə-", "wə", "and", "ja.morpheme.hebrew_coord_we", 3),
    CONTACT_LOCATIVE_MORPHEME: (
        "-ənk", "ənk", "LOC", "ja.morpheme.munsee_locative_enk", 1
    ),
    CONTACT_WHERE: ("efo", "efo", "where.static", "ja.lexeme.hebrew_eifo_where", 2),
    "ja.lexeme.contact_house": ("bayit", "bayit", "house", "ja.lexeme.hebrew_bayit", 3),
    "ja.lexeme.contact_room": ("xeder", "xeder", "room", "ja.lexeme.hebrew_heder_room", 2),
    "ja.lexeme.contact_table": (
        "šulxan", "šulxan", "table", "ja.lexeme.hebrew_shulhan_table", 2
    ),
    "ja.lexeme.contact_child": ("yeled", "yeled", "child", "ja.lexeme.hebrew_yeled_child", 2),
    "ja.lexeme.contact_ice": (
        "mohkaməy", "mohkaməy", "ice", "ja.lexeme.munsee_mohkamay_ice", 2
    ),
    "ja.lexeme.contact_be_there_ai": (
        "apii-", "apii", "be.located", "ja.lexeme.munsee_apii_be_there", 1
    ),
    "ja.lexeme.contact_sit_ai": (
        "ləmatapii-", "ləmatapii", "sit", "ja.lexeme.munsee_lematapii_sit", 1
    ),
    "ja.lexeme.contact_stand_ai": (
        "niipawii-", "niipaw~ii", "stand~AI", "ja.lexeme.munsee_niipawii_stand", 1
    ),
}
CONTACT_HOST_REALIZATIONS = {
    "road": "aanay",
    "ice": "mohkaməy",
    "bed": "apiinay",
    "house": "bayit",
    "room": "xeder",
    "table": "šulxan",
}
POSTURE_CELL_FORMS = {
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
STATIC_CLAUSE_CONTRACTS = {
    "ja.sentence.static_person_in_room": {
        "components": (
            ("ja.lexeme.contact_person", "overt third-singular subject", "adam"),
            (
                "ja.lexeme.contact_be_there_ai",
                "AI predicate stem inside third-singular cell",
                "apii",
            ),
            ("ja.phrase.static_in_room", "static locative setting", "xederənk"),
        ),
        "surface": "adam apiiw xederənk",
        "participant_tags": {"third-singular"},
    },
    "ja.sentence.static_child_sits_house": {
        "components": (
            ("ja.lexeme.contact_child", "overt third-singular subject", "yeled"),
            (
                "ja.lexeme.contact_sit_ai",
                "AI predicate stem inside third-singular cell",
                "ləmatapii",
            ),
            ("ja.phrase.static_in_house", "static locative setting", "bayitənk"),
        ),
        "surface": "yeled ləmatapiiw bayitənk",
        "participant_tags": {"third-singular"},
    },
    "ja.sentence.static_we_sit_table_inclusive": {
        "components": (
            (
                "ja.lexeme.contact_sit_ai",
                "AI predicate stem inside inclusive first-plural cell",
                "ləmatapii",
            ),
            ("ja.phrase.static_at_table", "static locative setting", "šulxanənk"),
        ),
        "surface": "kələmatapiihna šulxanənk",
        "participant_tags": {"first-plural", "inclusive"},
    },
    "ja.sentence.static_we_sit_house_exclusive": {
        "components": (
            (
                "ja.lexeme.contact_sit_ai",
                "AI predicate stem inside exclusive first-plural cell",
                "ləmatapii",
            ),
            ("ja.phrase.static_in_house", "static locative setting", "bayitənk"),
        ),
        "surface": "nələmatapiihna bayitənk",
        "participant_tags": {"first-plural", "exclusive"},
    },
    "ja.sentence.static_child_stands_road": {
        "components": (
            ("ja.lexeme.contact_child", "overt third-singular subject", "yeled"),
            (
                "ja.lexeme.contact_stand_ai",
                "AI predicate stem inside third-singular cell",
                "niipawii",
            ),
            ("ja.phrase.static_on_road", "static locative setting", "aaneenk"),
        ),
        "surface": "yeled niipawiiw aaneenk",
        "participant_tags": {"third-singular"},
    },
    "ja.sentence.static_they_in_house": {
        "components": (
            (
                "ja.lexeme.contact_be_there_ai",
                "AI predicate stem inside third-plural cell",
                "apii",
            ),
            ("ja.phrase.static_in_house", "static locative setting", "bayitənk"),
        ),
        "surface": "apiiwak bayitənk",
        "participant_tags": {"third-plural"},
    },
}
STATIC_WHERE_CONTRACTS = {
    "ja.sentence.question_where_person": {
        "components": (
            (
                CONTACT_WHERE,
                "clause-initial static locative interrogative",
                "efo",
            ),
            ("ja.lexeme.contact_person", "overt third-singular subject", "adam"),
            (
                "ja.lexeme.contact_be_there_ai",
                "AI predicate stem inside third-singular cell",
                "apii",
            ),
        ),
        "surface": "efo adam apiiw",
        "participant_tags": {"question", "third-singular"},
    },
    "ja.sentence.question_where_we_sit_inclusive": {
        "components": (
            (
                CONTACT_WHERE,
                "clause-initial static locative interrogative",
                "efo",
            ),
            (
                "ja.lexeme.contact_sit_ai",
                "AI predicate stem inside inclusive first-plural cell",
                "ləmatapii",
            ),
        ),
        "surface": "efo kələmatapiihna",
        "participant_tags": {"question", "first-plural", "inclusive"},
    },
}


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


def _language_record_inputs(record: dict[str, Any]) -> list[str]:
    formation = record.get("formation")
    if not isinstance(formation, dict):
        return []
    inputs = formation.get("inputs")
    if not isinstance(inputs, list):
        return []
    return [
        str(item.get("input_id"))
        for item in inputs
        if isinstance(item, dict) and item.get("input_type") == "language_record"
    ]


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
    value = re.sub(r"\b(?:not|no|without|neither)\b[^.;]*(?=$|[.;])", " ", value)
    return any(re.search(pattern, value) for pattern in NARRATIVE_SEMANTIC_PATTERNS)


def _asserts_tam_or_obviation(value: str) -> bool:
    value = re.sub(r"\b(?:not|no|without|neither)\b[^.;]*(?=$|[.;])", " ", value)
    return any(re.search(pattern, value) for pattern in TAM_OBVIATION_SEMANTIC_PATTERNS)


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
            (CONTACT_COORDINATOR, "coordinator", "wə"),
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
            _constructions(phrase) != {CONTACT_NOMINAL_COORDINATION}
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
        relations = finite.get("relations", {})
        expected_dependencies = [CONTACT_COORDINATOR, CONTACT_NOMINAL_COORDINATION]
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
        if (
            relations.get("depends_on") != expected_dependencies
            or relations.get("dependency_revisions")
            != {CONTACT_COORDINATOR: 1, CONTACT_NOMINAL_COORDINATION: 1}
            or _language_record_inputs(finite) != expected_dependencies
        ):
            findings.append(
                f"{FINITE_COORDINATION}: finite coordination must retain its exact contact coordinator dependencies"
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
            or components[1].get("record_id") != CONTACT_COORDINATOR
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


def _asserts_direction(value: str) -> bool:
    # The records retain explicit negative cautions such as “not a motion path.”
    # Remove their local scope before looking for a positive directional claim.
    value = re.sub(r"\b(?:not|no|without|neither)\b[^.;]*(?=$|[.;])", " ", value)
    patterns = (
        r"\bwhere to\b",
        r"\bwhere from\b",
        r"\bwhither\b",
        r"\bwhence\b",
        r"\btoward\b",
        r"\baway from\b",
        r"\bdestination\b",
        r"\bgoal\b",
        r"\bsource location\b",
        r"\bpath\b",
        r"\broute\b",
        r"\bdirectional\b",
    )
    return any(re.search(pattern, value) for pattern in patterns)


def _component_signature(record: dict[str, Any]) -> tuple[tuple[Any, Any, Any], ...]:
    return tuple(
        (
            component.get("record_id"),
            component.get("role"),
            component.get("realization"),
        )
        for component in _components(record)
    )


def _participant_tags(record: dict[str, Any]) -> set[str]:
    known = {
        "first-plural",
        "inclusive",
        "exclusive",
        "third-singular",
        "third-plural",
        "question",
    }
    return {
        tag
        for tag in record.get("metadata", {}).get("tags", [])
        if isinstance(tag, str) and tag in known
    }


def evaluate_static_place_compositions(
    records: Sequence[dict[str, Any]],
) -> list[str]:
    """Enforce the closed static-locative and location/posture enrichment."""

    records_by_id = {
        record["id"]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    tranche_markers = {
        SOURCE_STATIC_LOCATIVE,
        SOURCE_AI_PERSON,
        CONTACT_STATIC_LOCATIVE,
        CONTACT_POSTURE_AI,
        CONTACT_STATIC_CLAUSE,
        CONTACT_STATIC_WHERE,
        *[value[1] for value in CONTACT_LOCATIVE_CELLS.values()],
        *STATIC_CLAUSE_CONTRACTS,
        *STATIC_WHERE_CONTRACTS,
    }
    if not tranche_markers.intersection(records_by_id):
        return []

    findings: list[str] = []

    for record_id, contract in SOURCE_RECORD_CONTRACTS.items():
        record = records_by_id.get(record_id)
        if record is None:
            findings.append(f"{record_id}: required source evidence record is missing")
            continue
        form = record.get("forms", {}).get("judeo_algonquin", {})
        evidence = record.get("source_evidence")
        first_evidence = evidence[0] if isinstance(evidence, list) and len(evidence) == 1 else {}
        actual = (
            form.get("romanization"),
            form.get("segmentation"),
            form.get("morpheme_gloss"),
            record.get("metadata", {}).get("lexical_layer"),
            first_evidence.get("locator"),
            first_evidence.get("source_form"),
        )
        if actual != contract:
            findings.append(
                f"{record_id}: source form, analysis, layer, and cited evidence boundary must remain exact"
            )

    for record_id, contract in CONTACT_ATOMIC_CONTRACTS.items():
        record = records_by_id.get(record_id)
        if record is None:
            findings.append(f"{record_id}: required contact atomic overlay is missing")
            continue
        romanization, segmentation, gloss, dependency_id, dependency_revision = contract
        form = record.get("forms", {}).get("judeo_algonquin", {})
        relations = record.get("relations", {})
        if (
            form.get("romanization") != romanization
            or form.get("segmentation") != segmentation
            or form.get("morpheme_gloss") != gloss
            or record.get("metadata", {}).get("lexical_layer")
            != "direct_contact_inheritance"
            or relations.get("depends_on") != [dependency_id]
            or relations.get("dependency_revisions")
            != {dependency_id: dependency_revision}
        ):
            findings.append(
                f"{record_id}: contact atomic form and revision-pinned donor overlay must remain exact"
            )

    source_locative = records_by_id.get(SOURCE_STATIC_LOCATIVE)
    if source_locative is None:
        findings.append(f"{SOURCE_STATIC_LOCATIVE}: exact source evidence is missing")
    else:
        paradigm = source_locative.get("paradigm")
        cells = paradigm.get("cells", []) if isinstance(paradigm, dict) else []
        actual: dict[str, dict[str, Any]] = {}
        for cell in cells:
            features = cell.get("features") if isinstance(cell, dict) else None
            if not isinstance(features, dict) or set(features) != {"host"}:
                findings.append(
                    f"{SOURCE_STATIC_LOCATIVE}: source cells require exactly the host feature"
                )
                continue
            actual[str(features["host"])] = cell
        if set(actual) != set(SOURCE_LOCATIVE_CELLS):
            findings.append(
                f"{SOURCE_STATIC_LOCATIVE}: source paradigm must contain exactly road and ice"
            )
        for host, expected in SOURCE_LOCATIVE_CELLS.items():
            cell = actual.get(host)
            if cell is not None and (
                cell.get("romanization"),
                cell.get("segmentation"),
                cell.get("morpheme_gloss"),
                cell.get("meaning"),
                cell.get("status"),
            ) != expected:
                findings.append(
                    f"{SOURCE_STATIC_LOCATIVE}: {host} source cell must remain exact"
                )

    source_ai = records_by_id.get(SOURCE_AI_PERSON)
    if source_ai is None:
        findings.append(f"{SOURCE_AI_PERSON}: seven-way source table is missing")
    else:
        paradigm = source_ai.get("paradigm")
        cells = paradigm.get("cells", []) if isinstance(paradigm, dict) else []
        actual_source_ai: dict[tuple[str, str, str], dict[str, Any]] = {}
        for cell in cells:
            features = cell.get("features") if isinstance(cell, dict) else None
            if not isinstance(features, dict):
                continue
            key = (
                str(features.get("person")),
                str(features.get("number")),
                str(features.get("clusivity")),
            )
            if key in actual_source_ai:
                findings.append(f"{SOURCE_AI_PERSON}: duplicate source participant cell {key!r}")
            actual_source_ai[key] = cell
            if (
                set(features) != {"person", "number", "clusivity", "order", "class"}
                or features.get("order") != "independent"
                or features.get("class") != "AI"
                or cell.get("status") != "attested_pattern"
            ):
                findings.append(
                    f"{SOURCE_AI_PERSON}: every source cell must remain an independent AI attested pattern"
                )
            expected = SOURCE_AI_CELLS.get(key)
            if expected is not None and (
                cell.get("romanization"),
                cell.get("segmentation"),
                cell.get("morpheme_gloss"),
                cell.get("meaning"),
            ) != expected:
                findings.append(
                    f"{SOURCE_AI_PERSON}: {key!r} affix pattern and participant meaning must remain exact"
                )
        if set(actual_source_ai) != set(SOURCE_AI_CELLS) or len(cells) != 7:
            findings.append(
                f"{SOURCE_AI_PERSON}: source table must contain exactly seven participant patterns"
            )

    coordinator = records_by_id.get(CONTACT_COORDINATOR)
    nominal_coordination = records_by_id.get(CONTACT_NOMINAL_COORDINATION)
    if coordinator is None or nominal_coordination is None:
        findings.append(
            f"{CONTACT_NOMINAL_COORDINATION}: contact ordinary coordination layer is incomplete"
        )
    else:
        layer = coordinator.get("metadata", {}).get("lexical_layer")
        spec = nominal_coordination.get("construction_spec")
        tags = nominal_coordination.get("metadata", {}).get("tags", [])
        relations = nominal_coordination.get("relations", {})
        if (
            layer != "direct_contact_inheritance"
            or not isinstance(spec, dict)
            or spec.get("productivity") != "limited"
            or "narrative-firewall" not in tags
            or relations.get("depends_on") != [CONTACT_COORDINATOR]
            or relations.get("dependency_revisions") != {CONTACT_COORDINATOR: 1}
            or _language_record_inputs(nominal_coordination) != [CONTACT_COORDINATOR]
        ):
            findings.append(
                f"{CONTACT_NOMINAL_COORDINATION}: ordinary contact coordination must remain limited and firewalled with its exact contact coordinator dependency"
            )

    locative = records_by_id.get(CONTACT_STATIC_LOCATIVE)
    if locative is None:
        findings.append(f"{CONTACT_STATIC_LOCATIVE}: contact locative is missing")
    else:
        spec = locative.get("construction_spec")
        tags = locative.get("metadata", {}).get("tags", [])
        restrictions = " ".join(spec.get("restrictions", [])) if isinstance(spec, dict) else ""
        if (
            not isinstance(spec, dict)
            or spec.get("productivity") != "limited"
            or "contact-grammar" not in tags
            or "static-only" not in tags
            or not all(word in restrictions.lower() for word in ("goal", "source", "path"))
        ):
            findings.append(
                f"{CONTACT_STATIC_LOCATIVE}: six-host static construction and direction firewall are required"
            )
        paradigm = locative.get("paradigm")
        cells = paradigm.get("cells", []) if isinstance(paradigm, dict) else []
        actual_cells: dict[str, dict[str, Any]] = {}
        for cell in cells:
            features = cell.get("features") if isinstance(cell, dict) else None
            if not isinstance(features, dict) or set(features) != {
                "host",
                "semantic_role",
            }:
                findings.append(
                    f"{CONTACT_STATIC_LOCATIVE}: every cell requires host and semantic_role"
                )
                continue
            host = str(features["host"])
            if host in actual_cells:
                findings.append(f"{CONTACT_STATIC_LOCATIVE}: duplicate host cell {host}")
            actual_cells[host] = cell
            if (
                features.get("semantic_role") != "static_location"
                or cell.get("status") != "adapted_candidate"
            ):
                findings.append(
                    f"{CONTACT_STATIC_LOCATIVE}: {host} must remain a static adapted candidate"
                )
        if set(actual_cells) != set(CONTACT_LOCATIVE_CELLS) or len(cells) != 6:
            findings.append(
                f"{CONTACT_STATIC_LOCATIVE}: paradigm must contain exactly the six licensed hosts"
            )
        for host, (_, _, expected_surface) in CONTACT_LOCATIVE_CELLS.items():
            cell = actual_cells.get(host)
            if cell is not None and cell.get("romanization") != expected_surface:
                findings.append(
                    f"{CONTACT_STATIC_LOCATIVE}: {host} surface must be {expected_surface}"
                )

    for host, (host_id, phrase_id, expected_surface) in CONTACT_LOCATIVE_CELLS.items():
        phrase = records_by_id.get(phrase_id)
        if phrase is None:
            findings.append(f"{phrase_id}: required static locative phrase is missing")
            continue
        expected_components = (
            (host_id, "locative host", CONTACT_HOST_REALIZATIONS[host]),
            (CONTACT_LOCATIVE_MORPHEME, "locative suffix", "ənk"),
        )
        signature = _component_signature(phrase)
        if (
            signature != expected_components
            or _constructions(phrase) != {CONTACT_STATIC_LOCATIVE}
        ):
            findings.append(
                f"{phrase_id}: phrase must use its contact host followed by contact -ənk"
            )
        surface = phrase.get("forms", {}).get("judeo_algonquin", {}).get("romanization")
        if surface != expected_surface:
            findings.append(f"{phrase_id}: surface must be {expected_surface}")
        if _asserts_direction(_positive_semantic_text(phrase)):
            findings.append(f"{phrase_id}: static phrase may not claim direction or path")

    posture = records_by_id.get(CONTACT_POSTURE_AI)
    if posture is None:
        findings.append(f"{CONTACT_POSTURE_AI}: contact posture paradigm is missing")
    else:
        spec = posture.get("construction_spec")
        tags = posture.get("metadata", {}).get("tags", [])
        relations = posture.get("relations", {})
        expected_dependencies = {SOURCE_AI_PERSON, *POSTURE_STEMS}
        expected_revisions = {record_id: 1 for record_id in expected_dependencies}
        allomorphy = " ".join(spec.get("allomorphy", [])) if isinstance(spec, dict) else ""
        restrictions = " ".join(spec.get("restrictions", [])) if isinstance(spec, dict) else ""
        if (
            not isinstance(spec, dict)
            or spec.get("productivity") != "limited"
            or "contact-grammar" not in tags
            or "narrative-firewall" not in tags
            or "mandatory" not in allomorphy.lower()
            or "r10" not in allomorphy.lower()
            or "r13" not in allomorphy.lower()
            or "obviation" not in restrictions.lower()
            or set(relations.get("depends_on", [])) != expected_dependencies
            or relations.get("dependency_revisions") != expected_revisions
        ):
            findings.append(
                f"{CONTACT_POSTURE_AI}: transparent limited paradigm and explicit source-rule firewalls are required"
            )
        paradigm = posture.get("paradigm")
        cells = paradigm.get("cells", []) if isinstance(paradigm, dict) else []
        actual_posture: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        feature_names = {"predicate", "person", "number", "clusivity", "order", "class"}
        for cell in cells:
            features = cell.get("features") if isinstance(cell, dict) else None
            if not isinstance(features, dict) or set(features) != feature_names:
                findings.append(
                    f"{CONTACT_POSTURE_AI}: every cell must declare exactly six licensed features"
                )
                continue
            key = (
                str(features["predicate"]),
                str(features["person"]),
                str(features["number"]),
                str(features["clusivity"]),
            )
            if key in actual_posture:
                findings.append(f"{CONTACT_POSTURE_AI}: duplicate cell {key!r}")
            actual_posture[key] = cell
            if (
                features.get("order") != "independent"
                or features.get("class") != "AI"
                or cell.get("status") != "adapted_candidate"
            ):
                findings.append(
                    f"{CONTACT_POSTURE_AI}: {key!r} must remain an independent AI adapted candidate"
                )
            meaning = str(cell.get("meaning", ""))
            if (
                key[3] == "inclusive"
                and ("including the addressee" not in meaning or "excluding" in meaning)
            ) or (
                key[3] == "exclusive"
                and ("excluding the addressee" not in meaning or "including" in meaning)
            ):
                findings.append(
                    f"{CONTACT_POSTURE_AI}: {key!r} clusivity and meaning must agree"
                )
            gloss = str(cell.get("morpheme_gloss", ""))
            if "INCL" in gloss or "EXCL" in gloss:
                findings.append(
                    f"{CONTACT_POSTURE_AI}: {key!r} must not put clusivity on an isolated affix"
                )
        if set(actual_posture) != set(POSTURE_CELL_FORMS) or len(cells) != 21:
            findings.append(
                f"{CONTACT_POSTURE_AI}: paradigm must contain exactly twenty-one licensed cells"
            )
        for key, expected_surface in POSTURE_CELL_FORMS.items():
            cell = actual_posture.get(key)
            if cell is not None and cell.get("romanization") != expected_surface:
                findings.append(
                    f"{CONTACT_POSTURE_AI}: {key!r} surface must be {expected_surface}"
                )

    expected_static_constructions = {CONTACT_POSTURE_AI, CONTACT_STATIC_CLAUSE}
    for record_id, contract in STATIC_CLAUSE_CONTRACTS.items():
        sentence = records_by_id.get(record_id)
        if sentence is None:
            findings.append(f"{record_id}: required static clause is missing")
            continue
        if _constructions(sentence) != expected_static_constructions:
            findings.append(
                f"{record_id}: must declare exactly posture morphology and static clause syntax"
            )
        if _component_signature(sentence) != contract["components"]:
            findings.append(f"{record_id}: component identities, roles, or order violate its contract")
        surface = sentence.get("forms", {}).get("judeo_algonquin", {}).get("romanization")
        if surface != contract["surface"]:
            findings.append(f"{record_id}: surface must be {contract['surface']}")
        if _participant_tags(sentence) != contract["participant_tags"]:
            findings.append(f"{record_id}: participant tags must match its finite cell")
        registers = sentence.get("metadata", {}).get("registers", [])
        tags = set(sentence.get("metadata", {}).get("tags", []))
        required_firewalls = {"static-only", "narrative-firewall", "tam-firewall"}
        if not required_firewalls.issubset(tags) or (
            contract["participant_tags"].intersection({"third-singular", "third-plural"})
            and "obviation-deferred" not in tags
        ):
            findings.append(
                f"{record_id}: ordinary static clause requires static, TAM, narrative, and applicable obviation firewalls"
            )
        if (
            "narrative" in registers
            or NARRATIVE_FIREWALL_TAGS.intersection(tags)
            or _asserts_narrative_chain(_positive_semantic_text(sentence))
        ):
            findings.append(f"{record_id}: ordinary static clause may not claim narrative behavior")
        if (
            TAM_OBVIATION_TAGS.intersection(tags)
            or _asserts_tam_or_obviation(_positive_semantic_text(sentence))
        ):
            findings.append(
                f"{record_id}: ordinary static clause may not claim TAM or obviation"
            )
        if _asserts_direction(_positive_semantic_text(sentence)):
            findings.append(f"{record_id}: static clause may not claim direction or path")

    expected_where_constructions = {CONTACT_POSTURE_AI, CONTACT_STATIC_WHERE}
    locative_phrase_ids = {value[1] for value in CONTACT_LOCATIVE_CELLS.values()}
    for record_id, contract in STATIC_WHERE_CONTRACTS.items():
        sentence = records_by_id.get(record_id)
        if sentence is None:
            findings.append(f"{record_id}: required static where question is missing")
            continue
        components = _components(sentence)
        if _constructions(sentence) != expected_where_constructions:
            findings.append(
                f"{record_id}: must declare exactly posture morphology and static-where syntax"
            )
        if _component_signature(sentence) != contract["components"]:
            findings.append(f"{record_id}: efo-first component contract is violated")
        if not components or components[0].get("record_id") != CONTACT_WHERE:
            findings.append(f"{record_id}: contact efo must be first")
        if any(component.get("record_id") in locative_phrase_ids for component in components):
            findings.append(f"{record_id}: where question cannot state its missing locative answer")
        surface = sentence.get("forms", {}).get("judeo_algonquin", {}).get("romanization")
        if surface != contract["surface"]:
            findings.append(f"{record_id}: surface must be {contract['surface']}")
        if _participant_tags(sentence) != contract["participant_tags"]:
            findings.append(f"{record_id}: question participant tags must match its finite cell")
        if _asserts_direction(_positive_semantic_text(sentence)):
            findings.append(f"{record_id}: efo question may ask static location only")
        registers = sentence.get("metadata", {}).get("registers", [])
        tags = set(sentence.get("metadata", {}).get("tags", []))
        required_firewalls = {"static-only", "direction-firewall", "narrative-firewall", "tam-firewall"}
        if not required_firewalls.issubset(tags) or (
            contract["participant_tags"].intersection({"third-singular", "third-plural"})
            and "obviation-deferred" not in tags
        ):
            findings.append(
                f"{record_id}: static efo question requires direction, TAM, narrative, and applicable obviation firewalls"
            )
        if (
            "narrative" in registers
            or NARRATIVE_FIREWALL_TAGS.intersection(tags)
            or _asserts_narrative_chain(_positive_semantic_text(sentence))
        ):
            findings.append(f"{record_id}: ordinary efo question may not claim narrative behavior")
        if (
            TAM_OBVIATION_TAGS.intersection(tags)
            or _asserts_tam_or_obviation(_positive_semantic_text(sentence))
        ):
            findings.append(f"{record_id}: ordinary efo question may not claim TAM or obviation")

    return findings


MOTION_AI = "ja.construction.contact_ai_motion_independent"
DRINK_AI = "ja.construction.contact_ai_drink_independent"
FIND_ABSOLUTE = "ja.construction.contact_find_absolute_first_plural"
RELATOR_CLAUSE = "ja.construction.contact_ai_motion_relator_clause"
RELATOR_PHRASE = "ja.construction.contact_spatial_relator_phrase"

MOTION_SOURCE_CONTRACTS = {
    "ja.lexeme.hebrew_el_goal": (
        "el",
        "אֶל",
        "to; toward; motion or direction toward",
        "Preposition used especially after verbs of motion and direction.",
        "BDB headword אֵל / אֶל, preposition I; "
        "https://www.sefaria.org/BDB%2C_%D7%90%D6%B5%D7%9C",
        "high",
    ),
    "ja.lexeme.hebrew_min_source": (
        "min",
        "מִן־",
        "from; out of; away from; separation from",
        "Preposition of separation and source, including use after motion verbs.",
        "BDB headword מִן־, preposition; "
        "https://www.sefaria.org/BDB%2C_%D7%9E%D6%B4%D7%9F%D6%BE.1",
        "high",
    ),
    "ja.lexeme.hebrew_derekh_way": (
        "derekh",
        "דֶּרֶךְ",
        "way; road; path; journey",
        "Noun with physical and extended senses; only the physical route domain is "
        "selected here.",
        "BDB headword דֶּרֶךְ; "
        "https://www.sefaria.org/BDB%2C_%D7%93%D6%B6%D6%BC%D6%B6%D7%A8%D6%B6%D7%9A%D6%B0",
        "high",
    ),
    "ja.lexeme.munsee_alemesii_go_away": (
        "aləm-əsii-",
        "aləmsəw; /aləm-əsii-w/",
        "he goes away",
        "AI-final example analyzed as motion away plus AF /-əsii/ plus third person /-w/.",
        "O'Meara 1990, p. 130, §2.4.2.1, example 2.80",
        "high",
    ),
    "ja.lexeme.munsee_kwaxkii_return": (
        "kwaxk-ii-",
        "/kwaxk-ii-w/",
        "he comes/goes back",
        "Listed as a stable /-ii/ AI-final stem with third-person /-w/; the table "
        "supplies an analyzed form rather than a separate surface.",
        "O'Meara 1990, p. 134, §2.4.2.2, example 2.83b",
        "high",
    ),
    "ja.lexeme.munsee_maachii_go_home": (
        "maač-ii-",
        "/maač-ii-w/",
        "he goes home",
        "Listed as a stable /-ii/ AI-final stem with third-person /-w/; the table "
        "supplies an analyzed form rather than a separate surface.",
        "O'Meara 1990, p. 134, §2.4.2.2, example 2.83b",
        "high",
    ),
    "ja.lexeme.munsee_menee_drink": (
        "mən-ee-",
        "məneew; /mən-ee-w/",
        "he drinks",
        "AI-final example analyzed as /mən-ee-w/ with interlinear drink-AI-3; the "
        "passage says segmentation of some examples is uncertain.",
        "O'Meara 1990, p. 140, §2.4.2.3, example 2.88",
        "medium",
    ),
}

MOTION_CONTACT_CONTRACTS = {
    "ja.lexeme.contact_el_goal": (
        "el",
        "ja.lexeme.hebrew_el_goal",
        1,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_min_source": (
        "min",
        "ja.lexeme.hebrew_min_source",
        1,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_derex_route": (
        "derex",
        "ja.lexeme.hebrew_derekh_way",
        1,
        "contact_native_formation",
    ),
    "ja.lexeme.contact_go_away_ai": (
        "aləməsii-",
        "ja.lexeme.munsee_alemesii_go_away",
        1,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_return_ai": (
        "kwaxkii-",
        "ja.lexeme.munsee_kwaxkii_return",
        1,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_go_home_ai": (
        "maačii-",
        "ja.lexeme.munsee_maachii_go_home",
        1,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_drink_ai": (
        "mənee-",
        "ja.lexeme.munsee_menee_drink",
        1,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_find_animate": (
        "moxkaw-",
        "ja.lexeme.munsee_moxk_aw_find_animate",
        2,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_find_inanimate": (
        "moxkam-",
        "ja.lexeme.munsee_moxk_am_find_inanimate",
        2,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_door": (
        "delet",
        "ja.lexeme.hebrew_delet_door",
        2,
        "direct_contact_inheritance",
    ),
}

PARTICIPANT_BUNDLES = (
    ("first", "singular", "not_applicable"),
    ("second", "singular", "not_applicable"),
    ("third", "singular", "not_applicable"),
    ("first", "plural", "inclusive"),
    ("first", "plural", "exclusive"),
    ("second", "plural", "not_applicable"),
    ("third", "plural", "not_applicable"),
)
MOTION_CELL_FORMS = {
    "walk": (
        "nəpəməsiim",
        "kəpəməsiim",
        "pəməsiiw",
        "kəpəməsiihna",
        "nəpəməsiihna",
        "kəpəməsiihmwa",
        "pəməsiiwak",
    ),
    "go_away": (
        "nəaləməsiim",
        "kəaləməsiim",
        "aləməsiiw",
        "kəaləməsiihna",
        "nəaləməsiihna",
        "kəaləməsiihmwa",
        "aləməsiiwak",
    ),
    "return": (
        "nəkwaxkiim",
        "kəkwaxkiim",
        "kwaxkiiw",
        "kəkwaxkiihna",
        "nəkwaxkiihna",
        "kəkwaxkiihmwa",
        "kwaxkiiwak",
    ),
    "go_home": (
        "nəmaačiim",
        "kəmaačiim",
        "maačiiw",
        "kəmaačiihna",
        "nəmaačiihna",
        "kəmaačiihmwa",
        "maačiiwak",
    ),
}
DRINK_CELL_FORMS = (
    "nəməneem",
    "kəməneem",
    "məneew",
    "kəməneehna",
    "nəməneehna",
    "kəməneehmwa",
    "məneewak",
)
FIND_CELL_FORMS = {
    ("animate", "inclusive"): "kəmoxkawahna",
    ("animate", "exclusive"): "nəmoxkawahna",
    ("inanimate", "inclusive"): "kəmoxkamohna",
    ("inanimate", "exclusive"): "nəmoxkamohna",
}
RELATOR_PHRASE_FORMS = {
    ("goal", "house"): "el bayit",
    ("source", "house"): "min bayit",
    ("route", "road"): "derex aanay",
}
RELATOR_CLAUSE_FORMS = {
    ("goal", "walk", "child", "house"): "yeled pəməsiiw el bayit",
    ("source", "go_away", "child", "house"): "yeled aləməsiiw min bayit",
    ("route", "walk", "person", "road"): "adam pəməsiiw derex aanay",
}
FIND_SENTENCE_CONTRACTS = {
    "ja.sentence.action_we_find_person_inclusive": (
        "ja.lexeme.contact_find_animate",
        "ja.lexeme.contact_person",
        "inclusive",
        "kəmoxkawahna adam",
    ),
    "ja.sentence.action_we_find_person_exclusive": (
        "ja.lexeme.contact_find_animate",
        "ja.lexeme.contact_person",
        "exclusive",
        "nəmoxkawahna adam",
    ),
    "ja.sentence.action_we_find_door_inclusive": (
        "ja.lexeme.contact_find_inanimate",
        "ja.lexeme.contact_door",
        "inclusive",
        "kəmoxkamohna delet",
    ),
    "ja.sentence.action_we_find_door_exclusive": (
        "ja.lexeme.contact_find_inanimate",
        "ja.lexeme.contact_door",
        "exclusive",
        "nəmoxkamohna delet",
    ),
}


DOMESTIC_ABSOLUTE = "ja.construction.contact_domestic_absolute_subset"
DOMESTIC_SMALL_CHILD = "ja.construction.contact_small_child_phrase"
DOMESTIC_COACTIVITY = "ja.construction.contact_coactivity_yaxad"
DOMESTIC_EVENT_SETTING = "ja.construction.contact_domestic_event_setting"

DOMESTIC_SOURCE_CONTRACTS = {
    "ja.lexeme.munsee_mweh_w_eat_animate": (
        "mwəh-w-",
        "/mwəh-w-/; nəmohaaw /nə-mwəhw-aa-w/",
        "eat someone; I eat him",
        "TA member of a suppletive TA/TI eat pair; the finite example is first "
        "singular subject with third singular object.",
        "O'Meara 1990, p. 66, §2.1.1, example 2.6; p. 81, §2.1.5, example 2.33a",
        "high",
    ),
    "ja.lexeme.munsee_miichii_eat_inanimate": (
        "miičii-",
        "/miičii-/; nəmiičiin /nə-miičii-n/",
        "eat something; I eat it",
        "TI member of a suppletive TA/TI eat pair; the finite example is first "
        "singular with an Objective ending.",
        "O'Meara 1990, p. 66, §2.1.1, example 2.6; p. 81, §2.1.5, example 2.33a",
        "high",
    ),
    "ja.lexeme.munsee_peeshew_bring_animate": (
        "peešəw-",
        "mpeešəwaaw; /nə-peešəw-aa-w/",
        "I bring him",
        "TA member of a suppletive TA/TI pair; first singular subject and third "
        "singular object.",
        "O'Meara 1990, pp. 81-82, §2.1.5, example 2.33c",
        "high",
    ),
    "ja.lexeme.munsee_peel_bring_inanimate": (
        "peel-",
        "mpeeloon; /nə-peel-oo-n/",
        "I bring it",
        "TI2 member of a suppletive TA/TI pair; /peel-/ is the analyzed stem and "
        "/-oo-/ the displayed TI2 material.",
        "O'Meara 1990, p. 82, §2.1.5, example 2.33c",
        "high",
    ),
    "ja.lexeme.hebrew_yahad_together": (
        "yaḥad",
        "יַ֫חַד",
        "unitedness; in union; together",
        "Noun used adverbially, including together in community of action, place, "
        "or time.",
        "BDB headword יַ֫חַד, senses 1-2a; "
        "https://www.sefaria.org/BDB%2C_%D7%99%D6%B7%D6%AB%D7%97%D6%B7%D7%93",
        "high",
    ),
}

DOMESTIC_CONTACT_CONTRACTS = {
    "ja.lexeme.contact_eat_inanimate": (
        "miičii-",
        "ja.lexeme.munsee_miichii_eat_inanimate",
        1,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_bring_animate": (
        "peešəw-",
        "ja.lexeme.munsee_peeshew_bring_animate",
        1,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_bring_inanimate": (
        "peel-",
        "ja.lexeme.munsee_peel_bring_inanimate",
        1,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_together": (
        "yaxad",
        "ja.lexeme.hebrew_yahad_together",
        1,
        "direct_contact_inheritance",
    ),
    "ja.lexeme.contact_mother": (
        "em",
        "ja.lexeme.hebrew_em_mother",
        2,
        "direct_contact_inheritance",
    ),
}

DOMESTIC_CONTACT_EVIDENCE_CONTRACTS = {
    "ja.lexeme.contact_eat_inanimate": (
        "/miičii-/; nəmiičiin /nə-miičii-n/",
        "eat something; I eat it",
        "TI member of a suppletive pair; the contact Absolute is not "
        "source-attested by this lexical record.",
        "O'Meara 1990, p. 66, §2.1.1, example 2.6; p. 81, §2.1.5, example 2.33a",
        "high",
        "Contact truncation before the inanimate bridge and the bread/fruit "
        "inventory are project choices.",
    ),
    "ja.lexeme.contact_bring_animate": (
        "mpeešəwaaw; /nə-peešəw-aa-w/",
        "I bring him",
        "TA member of a suppletive bring pair.",
        "O'Meara 1990, pp. 81-82, §2.1.5, example 2.33c",
        "high",
        "The bare stem comes from analysis; contact cells and objects are new "
        "project grammar.",
    ),
    "ja.lexeme.contact_bring_inanimate": (
        "mpeeloon; /nə-peel-oo-n/",
        "I bring it",
        "TI2 member of a suppletive bring pair; the source finite form contains "
        "/-oo-/ after /peel-/.",
        "O'Meara 1990, p. 82, §2.1.5, example 2.33c",
        "high",
        "Contact o is a constructional class bridge, not a claim that source "
        "TI2 /-oo-/ transfers unchanged.",
    ),
    "ja.lexeme.contact_together": (
        "יַ֫חַד",
        "unitedness; together",
        "Noun used adverbially, including community in action.",
        "BDB headword יַ֫חַד, senses 1-2a; "
        "https://www.sefaria.org/BDB%2C_%D7%99%D6%B7%D6%AB%D7%97%D6%B7%D7%93",
        "high",
        "The postclausal position and plural-subject restriction are contact design.",
    ),
}

DOMESTIC_CONTACT_HISTORY_CLAIMS = {
    "ja.lexeme.contact_eat_inanimate":
        "O'Meara supports /miičii-/ as the TI member of a suppletive eat pair; "
        "all contact distribution and morphophonemics are project design.",
    "ja.lexeme.contact_bring_animate":
        "O'Meara supports analyzed /peešəw-/ in a printed TA bring form; every "
        "contact surface is an adapted candidate.",
    "ja.lexeme.contact_bring_inanimate":
        "O'Meara supports analyzed /peel-/ in a printed TI2 bring form; the "
        "contact bridge is not imported from that TI2 ending.",
    "ja.lexeme.contact_together":
        "BDB supports Hebrew yaḥad 'together'; contact x and the narrow "
        "postclausal coactivity distribution are project design.",
    "ja.lexeme.contact_mother":
        "The existing donor record supports Hebrew אֵם; the short-e contact "
        "realization and bounded syntax are project choices.",
}

DOMESTIC_CELL_FORMS = {
    ("eat_inanimate", "third_singular", "independent", "Absolute"): "miičow",
    ("eat_inanimate", "first_plural_inclusive", "independent", "Absolute"):
        "kəmiičohna",
    ("eat_inanimate", "first_plural_exclusive", "independent", "Absolute"):
        "nəmiičohna",
    ("bring_animate", "third_singular", "independent", "Absolute"): "peešəwaw",
    ("bring_animate", "first_plural_inclusive", "independent", "Absolute"):
        "kəpeešəwahna",
    ("bring_animate", "first_plural_exclusive", "independent", "Absolute"):
        "nəpeešəwahna",
    ("bring_inanimate", "third_singular", "independent", "Absolute"): "peelow",
    ("bring_inanimate", "first_plural_inclusive", "independent", "Absolute"):
        "kəpeelohna",
    ("bring_inanimate", "first_plural_exclusive", "independent", "Absolute"):
        "nəpeelohna",
}

DOMESTIC_CELL_DETAILS = {
    ("eat_inanimate", "third_singular", "independent", "Absolute"): (
        "miičow", "מִיצֹ׳וו", "miičii~o~w", "eat.TI~ABS.IN~3",
    ),
    ("eat_inanimate", "first_plural_inclusive", "independent", "Absolute"): (
        "kəmiičohna", "קְמִיצֹ׳הנַ", "kə~miičii~o~hna",
        "PERS.PFX~eat.TI~ABS.IN~1PL",
    ),
    ("eat_inanimate", "first_plural_exclusive", "independent", "Absolute"): (
        "nəmiičohna", "נְמִיצֹ׳הנַ", "nə~miičii~o~hna",
        "PERS.PFX~eat.TI~ABS.IN~1PL",
    ),
    ("bring_animate", "third_singular", "independent", "Absolute"): (
        "peešəwaw", "פֵּישְׁווַוו", "peešəw~a~w", "bring.TA~ABS.AN~3",
    ),
    ("bring_animate", "first_plural_inclusive", "independent", "Absolute"): (
        "kəpeešəwahna", "קְפֵּישְׁווַהנַ", "kə~peešəw~a~hna",
        "PERS.PFX~bring.TA~ABS.AN~1PL",
    ),
    ("bring_animate", "first_plural_exclusive", "independent", "Absolute"): (
        "nəpeešəwahna", "נְפֵּישְׁווַהנַ", "nə~peešəw~a~hna",
        "PERS.PFX~bring.TA~ABS.AN~1PL",
    ),
    ("bring_inanimate", "third_singular", "independent", "Absolute"): (
        "peelow", "פֵּילֹוו", "peel~o~w", "bring.TI~ABS.IN~3",
    ),
    ("bring_inanimate", "first_plural_inclusive", "independent", "Absolute"): (
        "kəpeelohna", "קְפֵּילֹהנַ", "kə~peel~o~hna",
        "PERS.PFX~bring.TI~ABS.IN~1PL",
    ),
    ("bring_inanimate", "first_plural_exclusive", "independent", "Absolute"): (
        "nəpeelohna", "נְפֵּילֹהנַ", "nə~peel~o~hna",
        "PERS.PFX~bring.TI~ABS.IN~1PL",
    ),
}

DOMESTIC_CONSTRUCTION_SPECS = {
    DOMESTIC_ABSOLUTE: {
        "host_classes": (
            "miičii- plus bare lexem or pri",
            "peešəw- plus bare adam or yeled",
            "peel- plus bare lexem, pri, or tiihinčəw",
        ),
        "ordering": (
            "overt lexical subject only in third-singular clauses",
            "finite predicate",
            "overt bare indefinite object",
        ),
        "allomorphy": (
            "TA uses contact a; TI uses contact o.",
            "miičii loses final ii before o: miičii-o becomes miičo.",
            "peešəw-a and peel-o concatenate without further change.",
        ),
        "restrictions": (
            "Exactly nine finite cells.",
            "Third-singular subjects are limited to bare adam, yeled, or em "
            "and cannot be omitted.",
            "Objects are mandatory, bare, nondefinite, and selected by the "
            "declared stem class; admitted count objects are singular.",
            "No definite, plural, possessed, incorporated, omitted, recipient, "
            "goal, source, or route object is licensed.",
            "No tense, aspect, modality, polarity, imperative, direct/inverse, "
            "proximate/obviative, wayyiqtol, weqatal, foreground, consequence, "
            "or center-shift value is supplied.",
        ),
        "counterexamples": (
            "miičii with adam or yeled is outside this tranche.",
            "peešəw with lexem and peel with yeled are class mismatches.",
            "Untruncated miičiio forms are invalid in this construction.",
            "Two third-person animate participants remain recoverable only "
            "through overt noun order; this is not narrative participant tracking.",
        ),
    },
    DOMESTIC_SMALL_CHILD: {
        "host_classes": ("exact pair: contact child plus contact small",),
        "ordering": ("noun", "postposed property word"),
        "allomorphy": ("katan remains invariant.",),
        "restrictions": (
            "No other noun or property word is licensed.",
            "No definiteness, plurality, possession, comparison, intensity, "
            "or predicate use.",
        ),
        "counterexamples": (
            "katan yeled is invalid in this construction.",
            "Interpreting small as young or dear is invalid.",
        ),
    },
    DOMESTIC_COACTIVITY: {
        "host_classes": (
            "inclusive eat-bread clause",
            "exclusive eat-bread clause",
            "inclusive eat-fruit clause",
            "exclusive eat-fruit clause",
        ),
        "ordering": ("complete predicate-object clause", "postposed yaxad"),
        "allomorphy": ("Invariant yaxad.",),
        "restrictions": (
            "Exactly four host clauses.",
            "No separate comitative NP, reciprocal reading, clause coordination, "
            "simultaneity-only reading, TAM, or narrative relation.",
        ),
        "counterexamples": (
            "yaxad cannot replace wə- between clauses.",
            "A singular clause cannot host yaxad here.",
            "Yaxad before the predicate is outside the construction.",
        ),
    },
    DOMESTIC_EVENT_SETTING: {
        "host_classes": (
            "yeled miičow lexem plus bayitənk",
            "kəmiičohna lexem plus bayitənk",
            "nəmiičohna lexem plus bayitənk",
            "kəmiičohna lexem plus šulxanənk",
        ),
        "ordering": (
            "finite predicate with any required lexical subject",
            "overt food object",
            "static setting phrase",
        ),
        "allomorphy": ("No additional allomorphy.",),
        "restrictions": (
            "Exactly four complete combinations.",
            "The setting is not possessed, plural, directional, definite, or "
            "incorporated.",
            "No arrival, source, path, duration, habituality, tense, or narrative "
            "sequence is contributed.",
        ),
        "counterexamples": (
            "bayitənk cannot replace the food object.",
            "el bayit and min bayit are not static settings here.",
            "The construction does not express our homes.",
        ),
    },
}

DOMESTIC_CORE_SENTENCE_CONTRACTS = {
    "ja.sentence.domestic_child_eats_bread": (
        ("ja.lexeme.contact_child", "ja.lexeme.contact_eat_inanimate", "ja.lexeme.contact_bread"),
        "yeled miičow lexem",
        None,
    ),
    "ja.sentence.domestic_mother_eats_fruit": (
        ("ja.lexeme.contact_mother", "ja.lexeme.contact_eat_inanimate", "ja.lexeme.contact_fruit"),
        "em miičow pri",
        None,
    ),
    "ja.sentence.domestic_we_eat_bread_inclusive": (
        ("ja.lexeme.contact_eat_inanimate", "ja.lexeme.contact_bread"),
        "kəmiičohna lexem",
        "inclusive",
    ),
    "ja.sentence.domestic_we_eat_bread_exclusive": (
        ("ja.lexeme.contact_eat_inanimate", "ja.lexeme.contact_bread"),
        "nəmiičohna lexem",
        "exclusive",
    ),
    "ja.sentence.domestic_we_eat_fruit_inclusive": (
        ("ja.lexeme.contact_eat_inanimate", "ja.lexeme.contact_fruit"),
        "kəmiičohna pri",
        "inclusive",
    ),
    "ja.sentence.domestic_we_eat_fruit_exclusive": (
        ("ja.lexeme.contact_eat_inanimate", "ja.lexeme.contact_fruit"),
        "nəmiičohna pri",
        "exclusive",
    ),
    "ja.sentence.domestic_child_brings_bread": (
        ("ja.lexeme.contact_child", "ja.lexeme.contact_bring_inanimate", "ja.lexeme.contact_bread"),
        "yeled peelow lexem",
        None,
    ),
    "ja.sentence.domestic_child_brings_cup": (
        ("ja.lexeme.contact_child", "ja.lexeme.contact_bring_inanimate", "ja.lexeme.contact_cup"),
        "yeled peelow tiihinčəw",
        None,
    ),
    "ja.sentence.domestic_mother_brings_fruit": (
        (
            "ja.lexeme.contact_mother",
            "ja.lexeme.contact_bring_inanimate",
            "ja.lexeme.contact_fruit",
        ),
        "em peelow pri",
        None,
    ),
    "ja.sentence.domestic_we_bring_child_inclusive": (
        ("ja.lexeme.contact_bring_animate", "ja.lexeme.contact_child"),
        "kəpeešəwahna yeled",
        "inclusive",
    ),
    "ja.sentence.domestic_we_bring_person_exclusive": (
        ("ja.lexeme.contact_bring_animate", "ja.lexeme.contact_person"),
        "nəpeešəwahna adam",
        "exclusive",
    ),
    "ja.sentence.domestic_mother_brings_child": (
        ("ja.lexeme.contact_mother", "ja.lexeme.contact_bring_animate", "ja.lexeme.contact_child"),
        "em peešəwaw yeled",
        None,
    ),
}

DOMESTIC_DERIVED_SENTENCE_CONTRACTS = {
    "ja.sentence.domestic_small_child_brings_bread": (
        (
            "ja.phrase.domestic_small_child",
            "ja.lexeme.contact_bring_inanimate",
            "ja.lexeme.contact_bread",
        ),
        (DOMESTIC_ABSOLUTE,),
        "yeled katan peelow lexem",
        None,
    ),
    "ja.sentence.domestic_we_eat_bread_together_inclusive": (
        ("ja.sentence.domestic_we_eat_bread_inclusive", "ja.lexeme.contact_together"),
        (DOMESTIC_COACTIVITY,),
        "kəmiičohna lexem yaxad",
        "inclusive",
    ),
    "ja.sentence.domestic_we_eat_bread_together_exclusive": (
        ("ja.sentence.domestic_we_eat_bread_exclusive", "ja.lexeme.contact_together"),
        (DOMESTIC_COACTIVITY,),
        "nəmiičohna lexem yaxad",
        "exclusive",
    ),
    "ja.sentence.domestic_we_eat_fruit_together_inclusive": (
        ("ja.sentence.domestic_we_eat_fruit_inclusive", "ja.lexeme.contact_together"),
        (DOMESTIC_COACTIVITY,),
        "kəmiičohna pri yaxad",
        "inclusive",
    ),
    "ja.sentence.domestic_we_eat_fruit_together_exclusive": (
        ("ja.sentence.domestic_we_eat_fruit_exclusive", "ja.lexeme.contact_together"),
        (DOMESTIC_COACTIVITY,),
        "nəmiičohna pri yaxad",
        "exclusive",
    ),
    "ja.sentence.domestic_we_eat_bread_house_inclusive": (
        ("ja.sentence.domestic_we_eat_bread_inclusive", "ja.phrase.static_in_house"),
        (DOMESTIC_EVENT_SETTING,),
        "kəmiičohna lexem bayitənk",
        "inclusive",
    ),
    "ja.sentence.domestic_we_eat_bread_house_exclusive": (
        ("ja.sentence.domestic_we_eat_bread_exclusive", "ja.phrase.static_in_house"),
        (DOMESTIC_EVENT_SETTING,),
        "nəmiičohna lexem bayitənk",
        "exclusive",
    ),
    "ja.sentence.domestic_we_eat_bread_table_inclusive": (
        ("ja.sentence.domestic_we_eat_bread_inclusive", "ja.phrase.static_at_table"),
        (DOMESTIC_EVENT_SETTING,),
        "kəmiičohna lexem šulxanənk",
        "inclusive",
    ),
    "ja.sentence.domestic_child_eats_bread_house": (
        ("ja.sentence.domestic_child_eats_bread", "ja.phrase.static_in_house"),
        (DOMESTIC_EVENT_SETTING,),
        "yeled miičow lexem bayitənk",
        None,
    ),
    "ja.sentence.domestic_we_sit_table_and_eat_bread_inclusive": (
        (
            "ja.sentence.static_we_sit_table_inclusive",
            "ja.morpheme.contact_coord_we",
            "ja.sentence.domestic_we_eat_bread_inclusive",
        ),
        ("ja.construction.contact_finite_coordination",),
        "kələmatapiihna šulxanənk wə-kəmiičohna lexem",
        "inclusive",
    ),
    "ja.sentence.domestic_we_eat_bread_and_drink_inclusive": (
        (
            "ja.sentence.domestic_we_eat_bread_inclusive",
            "ja.morpheme.contact_coord_we",
            "ja.sentence.action_we_drink_inclusive",
        ),
        ("ja.construction.contact_finite_coordination",),
        "kəmiičohna lexem wə-kəməneehna",
        "inclusive",
    ),
}

DOMESTIC_EXAMPLE_CONTRACTS = {
    "ja.phrase.domestic_small_child": (
        "a small child",
        (("nominal head", "yeled"), ("postposed physical-size property", "katan")),
    ),
    "ja.phrase.domestic_mother_and_child": (
        "mother and child",
        (("first conjunct", "em"), ("coordinator", "wə"),
         ("second conjunct", "yeled")),
    ),
    "ja.sentence.domestic_child_eats_bread": (
        "a child eats bread",
        (("overt third-singular subject", "yeled"),
         ("third-singular TI Absolute predicate", "miičow"),
         ("overt bare inanimate-class object", "lexem")),
    ),
    "ja.sentence.domestic_mother_eats_fruit": (
        "a mother eats fruit",
        (("overt third-singular subject", "em"),
         ("third-singular TI Absolute predicate", "miičow"),
         ("overt bare inanimate-class object", "pri")),
    ),
    "ja.sentence.domestic_we_eat_bread_inclusive": (
        "we including you eat bread",
        (("inclusive first-plural TI Absolute predicate", "kəmiičohna"),
         ("overt bare inanimate-class object", "lexem")),
    ),
    "ja.sentence.domestic_we_eat_bread_exclusive": (
        "we excluding you eat bread",
        (("exclusive first-plural TI Absolute predicate", "nəmiičohna"),
         ("overt bare inanimate-class object", "lexem")),
    ),
    "ja.sentence.domestic_we_eat_fruit_inclusive": (
        "we including you eat fruit",
        (("inclusive first-plural TI Absolute predicate", "kəmiičohna"),
         ("overt bare inanimate-class object", "pri")),
    ),
    "ja.sentence.domestic_we_eat_fruit_exclusive": (
        "we excluding you eat fruit",
        (("exclusive first-plural TI Absolute predicate", "nəmiičohna"),
         ("overt bare inanimate-class object", "pri")),
    ),
    "ja.sentence.domestic_child_brings_bread": (
        "a child brings bread",
        (("overt third-singular subject", "yeled"),
         ("third-singular TI Absolute predicate", "peelow"),
         ("overt bare inanimate-class object", "lexem")),
    ),
    "ja.sentence.domestic_child_brings_cup": (
        "a child brings a cup",
        (("overt subject", "yeled"),
         ("third-singular TI Absolute predicate", "peelow"),
         ("overt bare inanimate-class object", "tiihinčəw")),
    ),
    "ja.sentence.domestic_mother_brings_fruit": (
        "a mother brings fruit",
        (("overt subject", "em"),
         ("third-singular TI Absolute predicate", "peelow"),
         ("overt bare object", "pri")),
    ),
    "ja.sentence.domestic_we_bring_child_inclusive": (
        "we including you bring a child",
        (("inclusive first-plural TA Absolute predicate", "kəpeešəwahna"),
         ("overt bare animate-class object", "yeled")),
    ),
    "ja.sentence.domestic_we_bring_person_exclusive": (
        "we excluding you bring a person",
        (("exclusive first-plural TA Absolute predicate", "nəpeešəwahna"),
         ("overt bare animate-class object", "adam")),
    ),
    "ja.sentence.domestic_mother_brings_child": (
        "a mother brings a child",
        (("overt third-singular animate subject", "em"),
         ("third-singular TA Absolute predicate", "peešəwaw"),
         ("overt bare animate-class object", "yeled")),
    ),
    "ja.sentence.domestic_small_child_brings_bread": (
        "a small child brings bread",
        (("overt third-singular subject phrase", "yeled katan"),
         ("third-singular TI Absolute predicate", "peelow"),
         ("overt bare object", "lexem")),
    ),
    "ja.sentence.domestic_we_eat_bread_together_inclusive": (
        "we including you eat bread together",
        (("complete inclusive host clause", "kəmiičohna lexem"),
         ("postposed coactivity frame", "yaxad")),
    ),
    "ja.sentence.domestic_we_eat_bread_together_exclusive": (
        "we excluding you eat bread together",
        (("complete exclusive host clause", "nəmiičohna lexem"),
         ("postposed coactivity frame", "yaxad")),
    ),
    "ja.sentence.domestic_we_eat_fruit_together_inclusive": (
        "we including you eat fruit together",
        (("complete inclusive host clause", "kəmiičohna pri"),
         ("postposed coactivity frame", "yaxad")),
    ),
    "ja.sentence.domestic_we_eat_fruit_together_exclusive": (
        "we excluding you eat fruit together",
        (("complete exclusive host clause", "nəmiičohna pri"),
         ("postposed coactivity frame", "yaxad")),
    ),
    "ja.sentence.domestic_we_eat_bread_house_inclusive": (
        "we including you eat bread in a house",
        (("complete inclusive core clause", "kəmiičohna lexem"),
         ("static event setting", "bayitənk")),
    ),
    "ja.sentence.domestic_we_eat_bread_house_exclusive": (
        "we excluding you eat bread in a house",
        (("complete exclusive core clause", "nəmiičohna lexem"),
         ("static event setting", "bayitənk")),
    ),
    "ja.sentence.domestic_we_eat_bread_table_inclusive": (
        "we including you eat bread at a table",
        (("complete inclusive core clause", "kəmiičohna lexem"),
         ("static event setting", "šulxanənk")),
    ),
    "ja.sentence.domestic_child_eats_bread_house": (
        "a child eats bread in a house",
        (("complete third-singular core clause", "yeled miičow lexem"),
         ("static event setting", "bayitənk")),
    ),
    "ja.sentence.domestic_we_sit_table_and_eat_bread_inclusive": (
        "we including you sit at a table and eat bread",
        (("first complete inclusive clause", "kələmatapiihna šulxanənk"),
         ("coordinator", "wə"),
         ("second complete inclusive clause", "kəmiičohna lexem")),
    ),
    "ja.sentence.domestic_we_eat_bread_and_drink_inclusive": (
        "we including you eat bread and drink",
        (("first complete inclusive clause", "kəmiičohna lexem"),
         ("coordinator", "wə"),
         ("second complete inclusive clause", "kəməneehna")),
    ),
}


def _cell_map(
    record: dict[str, Any], feature_names: tuple[str, ...]
) -> tuple[dict[tuple[str, ...], dict[str, Any]], bool]:
    paradigm = record.get("paradigm")
    cells = paradigm.get("cells", []) if isinstance(paradigm, dict) else []
    result: dict[tuple[str, ...], dict[str, Any]] = {}
    duplicate = False
    for cell in cells:
        if not isinstance(cell, dict) or not isinstance(cell.get("features"), dict):
            continue
        key = tuple(str(cell["features"].get(name)) for name in feature_names)
        duplicate = duplicate or key in result
        result[key] = cell
    return result, duplicate


def evaluate_motion_action_compositions(
    records: Sequence[dict[str, Any]],
) -> list[str]:
    """Enforce the manually closed motion, action, and directional tranche."""

    records_by_id = {
        record["id"]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    if not any(
        "motion-action-enrichment" in record.get("metadata", {}).get("tags", [])
        for record in records_by_id.values()
    ):
        return []

    findings: list[str] = []
    for record_id, expected in MOTION_SOURCE_CONTRACTS.items():
        record = records_by_id.get(record_id)
        if record is None:
            findings.append(f"{record_id}: required source record is missing")
            continue
        evidence = record.get("source_evidence")
        item = evidence[0] if isinstance(evidence, list) and len(evidence) == 1 else {}
        actual = (
            record.get("forms", {}).get("judeo_algonquin", {}).get("romanization"),
            item.get("source_form"),
            item.get("source_meaning"),
            item.get("grammatical_information"),
            item.get("locator"),
            item.get("confidence"),
        )
        source_exact = (
            record.get("forms", {})
            .get("judeo_algonquin", {})
            .get("orthography", {})
            .get("source_exact")
        )
        if (
            actual != expected
            or (
                record_id.startswith("ja.lexeme.munsee_")
                and source_exact != item.get("source_form")
            )
            or record.get("metadata", {}).get("lexical_layer") != "donor_candidate"
        ):
            findings.append(
                f"{record_id}: cited orthographic source, evidence form, meaning, "
                "analysis, confidence, locator, and donor layer must remain exact"
            )

    for record_id, expected in MOTION_CONTACT_CONTRACTS.items():
        record = records_by_id.get(record_id)
        if record is None:
            findings.append(f"{record_id}: required contact record is missing")
            continue
        form, dependency, revision, layer = expected
        actual = (
            record.get("forms", {}).get("judeo_algonquin", {}).get("romanization"),
            record.get("relations", {}).get("depends_on"),
            record.get("relations", {}).get("dependency_revisions", {}).get(dependency),
            record.get("metadata", {}).get("lexical_layer"),
        )
        if actual != (form, [dependency], revision, layer):
            findings.append(
                f"{record_id}: contact form and revision-pinned ancestry must remain exact"
            )

    for contact_id in (
        "ja.lexeme.contact_go_away_ai",
        "ja.lexeme.contact_return_ai",
        "ja.lexeme.contact_go_home_ai",
        "ja.lexeme.contact_drink_ai",
    ):
        contact = records_by_id.get(contact_id, {})
        dependencies = contact.get("relations", {}).get("depends_on", [])
        donor = records_by_id.get(dependencies[0], {}) if len(dependencies) == 1 else {}
        contact_evidence = contact.get("source_evidence", [])
        donor_evidence = donor.get("source_evidence", [])
        contact_item = contact_evidence[0] if len(contact_evidence) == 1 else {}
        donor_item = donor_evidence[0] if len(donor_evidence) == 1 else {}
        evidence_keys = ("source_form", "source_meaning", "confidence", "locator")
        if tuple(contact_item.get(key) for key in evidence_keys) != tuple(
            donor_item.get(key) for key in evidence_keys
        ) or (
            contact.get("forms", {})
            .get("judeo_algonquin", {})
            .get("orthography", {})
            .get("source_exact")
            != donor_item.get("source_form")
        ):
            findings.append(
                f"{contact_id}: copied orthographic source, evidence form, meaning, "
                "confidence, and locator must match its revision-pinned donor"
            )
        grammatical_information = contact_item.get("grammatical_information", "")
        uncertainty = contact_item.get("uncertainty", "")
        if contact_id in {
            "ja.lexeme.contact_return_ai",
            "ja.lexeme.contact_go_home_ai",
        } and "prints no separate fused surface" not in grammatical_information:
            findings.append(
                f"{contact_id}: contact evidence must not present its fused stem as a "
                "printed donor surface"
            )
        if contact_id == "ja.lexeme.contact_drink_ai" and (
            "flags uncertainty for some segmentations" not in grammatical_information
            or "segmentation" not in uncertainty
        ):
            findings.append(
                f"{contact_id}: contact evidence must preserve the source segmentation "
                "caveat"
            )

    source_drink = records_by_id.get("ja.lexeme.munsee_menee_drink", {})
    contact_drink = records_by_id.get("ja.lexeme.contact_drink_ai", {})
    if (
        source_drink.get("forms", {}).get("judeo_algonquin", {}).get("morpheme_gloss")
        != "drink-AI"
        or contact_drink.get("forms", {})
        .get("judeo_algonquin", {})
        .get("morpheme_gloss")
        != "drink-AI"
    ):
        findings.append(
            "ja.lexeme.munsee_menee_drink: source interlinear drink-AI must remain "
            "explicit in donor and contact records"
        )
    derex = records_by_id.get("ja.lexeme.contact_derex_route", {})
    if derex.get("source_evidence"):
        findings.append(
            "ja.lexeme.contact_derex_route: route grammaticalization is project "
            "design, not direct source evidence"
        )

    for generic_id in ("ja.lexeme.munsee_aa_go", "ja.lexeme.munsee_paa_come"):
        generic = records_by_id.get(generic_id, {})
        tags = set(generic.get("metadata", {}).get("tags", []))
        if "source-class:unresolved" not in tags:
            findings.append(f"{generic_id}: generic motion stem must remain class-unresolved")
        if any(
            generic_id in _language_record_inputs(record)
            for record in records_by_id.values()
            if record.get("record_type") == "construction"
        ):
            findings.append(
                f"{generic_id}: unresolved generic stem may not license a finite construction"
            )

    motion = records_by_id.get(MOTION_AI)
    if motion is None:
        findings.append(f"{MOTION_AI}: required 28-cell motion construction is missing")
    else:
        cells, duplicate = _cell_map(
            motion, ("predicate", "person", "number", "clusivity", "order", "class")
        )
        expected_cells = {
            (predicate, person, number, clusivity, "independent", "AI"): surface
            for predicate, surfaces in MOTION_CELL_FORMS.items()
            for (person, number, clusivity), surface in zip(PARTICIPANT_BUNDLES, surfaces)
        }
        actual_surfaces = {key: cell.get("romanization") for key, cell in cells.items()}
        if duplicate or actual_surfaces != expected_cells:
            findings.append(
                f"{MOTION_AI}: paradigm must contain exactly the 28 declared motion cells"
            )
        for clusivity, expected_surface in (
            ("inclusive", "kəpəməsiihna"),
            ("exclusive", "nəpəməsiihna"),
        ):
            key = ("walk", "first", "plural", clusivity, "independent", "AI")
            if actual_surfaces.get(key) != expected_surface:
                findings.append(f"{MOTION_AI}: {clusivity} walk must match the chorus cell")

    drink = records_by_id.get(DRINK_AI)
    if drink is None:
        findings.append(f"{DRINK_AI}: required seven-cell drink construction is missing")
    else:
        cells, duplicate = _cell_map(
            drink, ("predicate", "person", "number", "clusivity", "order", "class")
        )
        expected_cells = {
            ("drink", person, number, clusivity, "independent", "AI"): surface
            for (person, number, clusivity), surface in zip(PARTICIPANT_BUNDLES, DRINK_CELL_FORMS)
        }
        actual_cells = {key: value.get("romanization") for key, value in cells.items()}
        if duplicate or actual_cells != expected_cells:
            findings.append(
                f"{DRINK_AI}: paradigm must contain exactly seven objectless drink cells"
            )

    find = records_by_id.get(FIND_ABSOLUTE)
    if find is None:
        findings.append(f"{FIND_ABSOLUTE}: required four-cell find construction is missing")
    else:
        cells, duplicate = _cell_map(
            find,
            (
                "predicate",
                "object_class",
                "person",
                "number",
                "clusivity",
                "order",
                "inflection",
            ),
        )
        expected_cells = {
            ("find", object_class, "first", "plural", clusivity, "independent", "Absolute"): surface
            for (object_class, clusivity), surface in FIND_CELL_FORMS.items()
        }
        actual_cells = {key: value.get("romanization") for key, value in cells.items()}
        if duplicate or actual_cells != expected_cells:
            findings.append(
                f"{FIND_ABSOLUTE}: paradigm must contain exactly four class-sensitive "
                "first-plural cells"
            )

    for construction_id, features, expected_forms in (
        (RELATOR_PHRASE, ("relation", "complement_host"), RELATOR_PHRASE_FORMS),
        (
            RELATOR_CLAUSE,
            ("relation", "predicate", "subject_host", "complement_host"),
            RELATOR_CLAUSE_FORMS,
        ),
    ):
        construction = records_by_id.get(construction_id)
        if construction is None:
            findings.append(f"{construction_id}: required directional construction is missing")
            continue
        cells, duplicate = _cell_map(construction, features)
        surfaces = {key: value.get("romanization") for key, value in cells.items()}
        has_static_locative = any("ənk" in str(value) for value in surfaces.values())
        if duplicate or surfaces != expected_forms or has_static_locative:
            findings.append(
                f"{construction_id}: closed relator cells and bare complements "
                "must remain exact"
            )

    for record_id, (stem_id, object_id, clusivity, surface) in FIND_SENTENCE_CONTRACTS.items():
        sentence = records_by_id.get(record_id)
        if sentence is None:
            findings.append(f"{record_id}: required find sentence is missing")
            continue
        components = _components(sentence)
        if (
            _constructions(sentence) != {FIND_ABSOLUTE}
            or [item.get("record_id") for item in components] != [stem_id, object_id]
            or sentence.get("forms", {}).get("judeo_algonquin", {}).get("romanization") != surface
            or _declared_clusivity(sentence) != clusivity
            or "overt-object" not in sentence.get("metadata", {}).get("tags", [])
        ):
            findings.append(
                f"{record_id}: find stem, object class, clusivity, and surface must agree"
            )

    for record in records_by_id.values():
        tags = set(record.get("metadata", {}).get("tags", []))
        if "motion-action-enrichment" not in tags:
            continue
        if record.get("record_type") in {"construction", "phrase", "sentence"}:
            if not {"tam-firewall", "narrative-firewall"}.issubset(tags):
                findings.append(
                    f"{record['id']}: ordinary enriched grammar requires TAM and "
                    "narrative firewalls"
                )
            text = _positive_semantic_text(record)
            if (
                _asserts_narrative_chain(text)
                or _asserts_tam_or_obviation(text)
                or re.search(
                    r"\b(?:walked|went|returned|drank|found|will|shall|usually|"
                    r"often|repeatedly|then|therefore)\b",
                    text,
                )
            ):
                findings.append(
                    f"{record['id']}: ordinary enriched grammar may not assert TAM, "
                    "obviation, or narrative chaining"
                )
        third_person = tags.intersection({"third-singular", "third-plural"})
        if (
            record.get("record_type") == "sentence"
            and third_person
            and "obviation-deferred" not in tags
        ):
            findings.append(f"{record['id']}: third-person sentence must defer obviation")

    return findings


def evaluate_domestic_action_compositions(
    records: Sequence[dict[str, Any]],
) -> list[str]:
    """Enforce the manually authored, deliberately closed domestic-action tranche."""

    records_by_id = {
        record["id"]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    required_ids = {
        *DOMESTIC_SOURCE_CONTRACTS,
        *DOMESTIC_CONTACT_CONTRACTS,
        DOMESTIC_ABSOLUTE,
        DOMESTIC_SMALL_CHILD,
        DOMESTIC_COACTIVITY,
        DOMESTIC_EVENT_SETTING,
        *DOMESTIC_CORE_SENTENCE_CONTRACTS,
        *DOMESTIC_DERIVED_SENTENCE_CONTRACTS,
        "ja.phrase.domestic_small_child",
        "ja.phrase.domestic_mother_and_child",
    }
    if not required_ids.intersection(records_by_id):
        return []

    findings: list[str] = []
    for record_id, expected in DOMESTIC_SOURCE_CONTRACTS.items():
        record = records_by_id.get(record_id)
        if record is None:
            findings.append(f"{record_id}: required domestic source record is missing")
            continue
        evidence = record.get("source_evidence")
        item = evidence[0] if isinstance(evidence, list) and len(evidence) == 1 else {}
        actual = (
            record.get("forms", {}).get("judeo_algonquin", {}).get("romanization"),
            item.get("source_form"),
            item.get("source_meaning"),
            item.get("grammatical_information"),
            item.get("locator"),
            item.get("confidence"),
        )
        source_exact = (
            record.get("forms", {})
            .get("judeo_algonquin", {})
            .get("orthography", {})
            .get("source_exact")
        )
        if (
            actual != expected
            or source_exact != item.get("source_form")
            or record.get("metadata", {}).get("lexical_layer") != "donor_candidate"
        ):
            findings.append(
                f"{record_id}: cited form, printed/analyzed boundary, meaning, "
                "analysis, locator, confidence, and donor layer must remain exact"
            )

    for record_id, expected in DOMESTIC_CONTACT_CONTRACTS.items():
        record = records_by_id.get(record_id)
        if record is None:
            findings.append(f"{record_id}: required domestic contact record is missing")
            continue
        form, dependency, revision, layer = expected
        actual = (
            record.get("forms", {}).get("judeo_algonquin", {}).get("romanization"),
            record.get("relations", {}).get("depends_on"),
            record.get("relations", {}).get("dependency_revisions", {}).get(dependency),
            record.get("metadata", {}).get("lexical_layer"),
        )
        if actual != (form, [dependency], revision, layer):
            findings.append(
                f"{record_id}: contact form and revision-pinned ancestry must remain exact"
            )
            continue
        history = record.get("formation", {}).get("historical_etymology", [])
        history_claim = (
            history[0].get("claim")
            if isinstance(history, list)
            and len(history) == 1
            and isinstance(history[0], dict)
            else None
        )
        if history_claim != DOMESTIC_CONTACT_HISTORY_CLAIMS[record_id]:
            findings.append(
                f"{record_id}: contact formation must preserve its exact "
                "source-versus-project boundary"
            )
        if record_id == "ja.lexeme.contact_mother":
            if record.get("source_evidence"):
                findings.append(
                    f"{record_id}: reused contact mother must not invent new source evidence"
                )
            continue
        contact_evidence = record.get("source_evidence", [])
        contact_item = contact_evidence[0] if len(contact_evidence) == 1 else {}
        evidence_keys = (
            "source_form",
            "source_meaning",
            "grammatical_information",
            "locator",
            "confidence",
            "uncertainty",
        )
        if tuple(contact_item.get(key) for key in evidence_keys) != (
            DOMESTIC_CONTACT_EVIDENCE_CONTRACTS[record_id]
        ):
            findings.append(
                f"{record_id}: contact evidence and its adaptation caution must "
                "remain exact"
            )

    absolute = records_by_id.get(DOMESTIC_ABSOLUTE)
    if absolute is None:
        findings.append(f"{DOMESTIC_ABSOLUTE}: required nine-cell construction is missing")
    else:
        cells, duplicate = _cell_map(
            absolute, ("predicate", "person_bundle", "order", "inflection")
        )
        cell_details = {
            key: (
                value.get("romanization"),
                value.get("hebrew_script"),
                value.get("segmentation"),
                value.get("morpheme_gloss"),
            )
            for key, value in cells.items()
        }
        if duplicate or cell_details != DOMESTIC_CELL_DETAILS:
            findings.append(
                f"{DOMESTIC_ABSOLUTE}: paradigm must contain exactly the nine declared "
                "class-sensitive cells with their script, analysis, and gloss"
            )
        eat_cells = [
            cell
            for key, cell in cells.items()
            if key[0] == "eat_inanimate"
        ]
        operations = absolute.get("formation", {}).get("operations", [])
        adaptation_text = " ".join(
            str(item.get("description", "")).lower()
            for item in operations
            if isinstance(item, dict)
            and item.get("operation") == "phonological_adaptation"
        )
        if (
            len(eat_cells) != 3
            or any("miičii~o" not in str(cell.get("segmentation")) for cell in eat_cells)
            or any("miičii-o" in str(cell.get("romanization")) for cell in eat_cells)
            or "delete stem-final ii" not in adaptation_text
        ):
            findings.append(
                f"{DOMESTIC_ABSOLUTE}: miičii must preserve its analyzed stem in "
                "segmentation and delete final ii before contact o on the surface"
            )

    phrase_contracts = {
        "ja.phrase.domestic_small_child": (
            ("ja.lexeme.contact_child", "ja.lexeme.contact_small"),
            {DOMESTIC_SMALL_CHILD},
            "yeled katan",
        ),
        "ja.phrase.domestic_mother_and_child": (
            (
                "ja.lexeme.contact_mother",
                "ja.morpheme.contact_coord_we",
                "ja.lexeme.contact_child",
            ),
            {"ja.construction.contact_nominal_coordination"},
            "em wə-yeled",
        ),
    }
    for record_id, (component_ids, constructions, surface) in phrase_contracts.items():
        record = records_by_id.get(record_id)
        if record is None:
            findings.append(f"{record_id}: required domestic phrase is missing")
            continue
        actual_ids = tuple(item.get("record_id") for item in _components(record))
        actual_surface = (
            record.get("forms", {}).get("judeo_algonquin", {}).get("romanization")
        )
        if (
            actual_ids != component_ids
            or _constructions(record) != constructions
            or actual_surface != surface
        ):
            findings.append(
                f"{record_id}: exact components, order, construction, and surface "
                "must remain closed"
            )

    for record_id, (component_ids, surface, clusivity) in (
        DOMESTIC_CORE_SENTENCE_CONTRACTS.items()
    ):
        record = records_by_id.get(record_id)
        if record is None:
            findings.append(f"{record_id}: required domestic core sentence is missing")
            continue
        actual_ids = tuple(item.get("record_id") for item in _components(record))
        actual_surface = (
            record.get("forms", {}).get("judeo_algonquin", {}).get("romanization")
        )
        if (
            actual_ids != component_ids
            or _constructions(record) != {DOMESTIC_ABSOLUTE}
            or actual_surface != surface
            or (clusivity is not None and _declared_clusivity(record) != clusivity)
        ):
            findings.append(
                f"{record_id}: subject, predicate class, overt object, clusivity, "
                "construction, and surface must agree"
            )

    for record_id, contract in DOMESTIC_DERIVED_SENTENCE_CONTRACTS.items():
        component_ids, construction_ids, surface, clusivity = contract
        record = records_by_id.get(record_id)
        if record is None:
            findings.append(f"{record_id}: required derived domestic sentence is missing")
            continue
        actual_ids = tuple(item.get("record_id") for item in _components(record))
        actual_surface = (
            record.get("forms", {}).get("judeo_algonquin", {}).get("romanization")
        )
        if (
            actual_ids != component_ids
            or _constructions(record) != set(construction_ids)
            or actual_surface != surface
            or (clusivity is not None and _declared_clusivity(record) != clusivity)
        ):
            findings.append(
                f"{record_id}: derived host, boundary, clusivity, construction, and "
                "surface must remain exact"
            )

    for construction_id, expected_spec in DOMESTIC_CONSTRUCTION_SPECS.items():
        construction = records_by_id.get(construction_id, {})
        construction_spec = construction.get("construction_spec", {})
        if any(
            tuple(construction_spec.get(field, [])) != expected
            for field, expected in expected_spec.items()
        ):
            findings.append(
                f"{construction_id}: closed hosts, order, allomorphy, restrictions, "
                "and counterexamples must remain exact"
            )

    for record_id, (expected_english, expected_details) in (
        DOMESTIC_EXAMPLE_CONTRACTS.items()
    ):
        record = records_by_id.get(record_id, {})
        english = record.get("forms", {}).get("english", [])
        senses = record.get("senses", [])
        sense = senses[0] if isinstance(senses, list) and len(senses) == 1 else {}
        idiomatic = sense.get("translations", {}).get("idiomatic", [])
        normalized_idiomatic = (
            re.sub(r"[^a-z]+", " ", idiomatic[0].lower()).strip()
            if isinstance(idiomatic, list)
            and len(idiomatic) == 1
            and isinstance(idiomatic[0], str)
            else None
        )
        normalized_expected = re.sub(
            r"[^a-z]+", " ", expected_english.lower()
        ).strip()
        actual_details = tuple(
            (item.get("role"), item.get("realization"))
            for item in _components(record)
        )
        definition = str(sense.get("definition", "")).lower()
        required_definition_pattern = (
            r"(?:physically small)"
            if record_id == "ja.phrase.domestic_small_child"
            else r"(?:joined|coordina)"
            if record_id == "ja.phrase.domestic_mother_and_child"
            else r"(?:jointly|joint participation)"
            if "together" in record_id
            else r"(?:accompan|causes)"
            if "bring" in record_id
            else r"(?:eat|consum)"
            if "eat" in record_id
            else r".+"
        )
        if (
            english != [expected_english]
            or normalized_idiomatic != normalized_expected
            or actual_details != expected_details
            or not re.search(required_definition_pattern, definition)
        ):
            findings.append(
                f"{record_id}: English meaning, sense, component roles, and "
                "component realizations must match the declared composition"
            )

    for record in records_by_id.values():
        tags = set(record.get("metadata", {}).get("tags", []))
        if "domestic-action-enrichment" not in tags:
            continue
        if record.get("record_type") in {"construction", "phrase", "sentence"} and (
            record.get("source_evidence")
        ):
            findings.append(
                f"{record['id']}: constructed domestic records must not invent "
                "direct source evidence"
            )
        if record.get("record_type") in {"construction", "sentence"}:
            semantic_text = _positive_semantic_text(record)
            if (
                _asserts_narrative_chain(semantic_text)
                or _asserts_tam_or_obviation(semantic_text)
                or re.search(
                    r"\b(?:ate|brought|sat|drank|will|shall|usually|often|"
                    r"repeatedly|then|therefore|consequently)\b",
                    semantic_text,
                )
            ):
                findings.append(
                    f"{record['id']}: domestic grammar may not assert TAM, "
                    "obviation, or narrative chaining"
                )
        if record.get("record_type") == "sentence" and not {
            "tam-firewall",
            "narrative-firewall",
        }.issubset(tags):
            findings.append(
                f"{record['id']}: domestic sentences require TAM and narrative firewalls"
            )
        if record.get("record_type") == "sentence" and not {
            "contact-clause",
            "componentwise-orthography",
        }.issubset(tags):
            findings.append(
                f"{record['id']}: domestic sentences require contact-clause and "
                "componentwise-orthography tags"
            )

    for record_id in required_ids:
        record = records_by_id.get(record_id)
        if record is not None and "domestic-action-enrichment" not in set(
            record.get("metadata", {}).get("tags", [])
        ):
            findings.append(
                f"{record_id}: required domestic record must retain its tranche tag"
            )

    expected_participants = {
        record_id: (
            {"first-plural", clusivity}
            if clusivity is not None
            else {"third-singular"}
        )
        for record_id, (_, _, clusivity) in DOMESTIC_CORE_SENTENCE_CONTRACTS.items()
    }
    expected_participants.update(
        {
            record_id: (
                {"first-plural", clusivity}
                if clusivity is not None
                else {"third-singular"}
            )
            for record_id, (_, _, _, clusivity) in (
                DOMESTIC_DERIVED_SENTENCE_CONTRACTS.items()
            )
        }
    )
    for record_id, expected_tags in expected_participants.items():
        record = records_by_id.get(record_id, {})
        if _participant_tags(record) != expected_tags:
            findings.append(
                f"{record_id}: participant and clusivity tags must match the "
                "declared finite cell"
            )

    for record_id in {
        "ja.sentence.domestic_we_bring_child_inclusive",
        "ja.sentence.domestic_we_bring_person_exclusive",
        "ja.sentence.domestic_mother_brings_child",
    }:
        tags = set(records_by_id.get(record_id, {}).get("metadata", {}).get("tags", []))
        if not {"direct-inverse-deferred", "obviation-deferred"}.issubset(tags):
            findings.append(
                f"{record_id}: animate-object clauses must defer direct/inverse "
                "and obviation"
            )

    return findings


def load_semantic_queries(path: str | Path) -> list[dict[str, Any]]:
    """Load a frozen retrieval set with enough metadata to explain each target."""

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path}: expected a non-empty JSON array")
    required = {"id", "query", "expected_id", "rationale"}
    queries: list[dict[str, Any]] = []
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


def load_typed_semantic_queries(path: str | Path) -> list[dict[str, Any]]:
    """Load a diagnostic set that separates query-language and contrast tests.

    ``acceptable_ids`` deliberately permits a query to retrieve either a concrete
    example or the construction that licenses it.  That keeps the evaluation from
    rewarding an arbitrary duplicate when the knowledge base stores both levels.
    """

    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path}: expected a non-empty JSON array")
    required = {"id", "query", "query_type", "acceptable_ids", "rationale"}
    allowed_types = {"english", "conlang", "compositional", "contrastive"}
    queries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError(
                f"{path}: typed query {index} must contain exactly {sorted(required)}"
            )
        for key in ("id", "query", "query_type", "rationale"):
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError(f"{path}: typed query {index} {key} must be non-empty")
        acceptable = item["acceptable_ids"]
        if (
            not isinstance(acceptable, list)
            or not acceptable
            or any(not isinstance(record_id, str) or not record_id for record_id in acceptable)
            or len(set(acceptable)) != len(acceptable)
        ):
            raise ValueError(
                f"{path}: typed query {index} acceptable_ids must be unique record ids"
            )
        if item["query_type"] not in allowed_types:
            raise ValueError(
                f"{path}: typed query {index} query_type must be one of {sorted(allowed_types)}"
            )
        if item["id"] in seen:
            raise ValueError(f"{path}: duplicate query id {item['id']}")
        seen.add(item["id"])
        queries.append({**item, "acceptable_ids": list(acceptable)})
    return queries


def evaluate_semantic_rankings(
    record_ids: Sequence[str],
    record_vectors: Sequence[Sequence[float]],
    queries: Sequence[dict[str, Any]],
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
        acceptable_ids = query.get("acceptable_ids")
        if acceptable_ids is None:
            acceptable_ids = [query["expected_id"]]
        if (
            not isinstance(acceptable_ids, list)
            or not acceptable_ids
            or any(not isinstance(record_id, str) for record_id in acceptable_ids)
        ):
            raise ValueError(f"query {query['id']} has invalid acceptable ids")
        unknown = sorted(set(acceptable_ids) - known)
        if unknown:
            raise ValueError(f"query {query['id']} expects unknown records {unknown}")
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
        acceptable_ranks = {
            item["id"]: index
            for index, item in enumerate(ranking, start=1)
            if item["id"] in acceptable_ids
        }
        expected_rank = min(acceptable_ranks.values())
        matched_id = min(
            acceptable_ranks,
            key=lambda record_id: (acceptable_ranks[record_id], record_id),
        )
        details.append(
            {
                **query,
                "matched_acceptable_id": matched_id,
                "expected_rank": expected_rank,
                "reciprocal_rank": 1.0 / expected_rank,
                "top_3": ranking[:3],
                "ranking": ranking,
            }
        )
    count = len(details)
    result = {
        "query_count": count,
        "recall_at_1": sum(item["expected_rank"] <= 1 for item in details) / count,
        "recall_at_3": sum(item["expected_rank"] <= 3 for item in details) / count,
        "mean_reciprocal_rank": sum(item["reciprocal_rank"] for item in details) / count,
        "queries": details,
    }
    query_types = sorted(
        {item.get("query_type") for item in details if isinstance(item.get("query_type"), str)}
    )
    if query_types:
        grouped: dict[str, dict[str, float | int]] = {}
        for query_type in query_types:
            group = [item for item in details if item.get("query_type") == query_type]
            grouped[query_type] = {
                "query_count": len(group),
                "recall_at_1": sum(item["expected_rank"] <= 1 for item in group) / len(group),
                "recall_at_3": sum(item["expected_rank"] <= 3 for item in group) / len(group),
                "mean_reciprocal_rank": sum(item["reciprocal_rank"] for item in group)
                / len(group),
            }
        result["by_query_type"] = grouped
    return result
