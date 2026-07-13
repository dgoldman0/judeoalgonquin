"""Deterministic composition checks that go beyond structural validation."""

from __future__ import annotations

import json
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
