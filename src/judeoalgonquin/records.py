"""JSONL loading and deterministic project-level validation."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

from .normalize import is_nfc, normalize_search, strip_hebrew_marks, unsafe_codepoints


ID_RE = re.compile(
    r"^ja\.(lexeme|morpheme|phrase|sentence|paragraph|construction)\.[a-z0-9][a-z0-9_-]*$"
)
SENSE_ID_RE = re.compile(
    r"^ja\.(lexeme|morpheme|phrase|sentence|paragraph|construction)\."
    r"[a-z0-9][a-z0-9_-]*\.sense\.[a-z0-9][a-z0-9_-]*$"
)
RECORD_TYPES = {"lexeme", "morpheme", "phrase", "sentence", "paragraph", "construction"}
STATUSES = {
    "draft",
    "candidate",
    "reviewed",
    "canonical",
    "deprecated",
    "superseded",
    "rejected",
}
REVIEWED_STATUSES = {"reviewed", "canonical", "deprecated", "superseded", "rejected"}
LEVELS = {"unassigned", "N1", "N2", "D1", "D2", "R1"}
RELATION_KEYS = {
    "depends_on",
    "related_to",
    "conflicts_with",
    "supersedes",
    "superseded_by",
}
NOTE_KEYS = {"translation", "grammar", "design"}
TOP_LEVEL_REQUIRED = {
    "schema_version",
    "id",
    "record_type",
    "revision",
    "status",
    "level",
    "forms",
    "senses",
    "grammatical_features",
    "notes",
    "formation",
    "source_evidence",
    "provenance",
    "relations",
    "metadata",
    "created_at",
    "updated_at",
    "change_note",
}
TOP_LEVEL_OPTIONAL = {"review", "narrative_analysis"}
ALLOWED_TOP_LEVEL = TOP_LEVEL_REQUIRED | TOP_LEVEL_OPTIONAL


class ValidationError(ValueError):
    def __init__(self, errors: Iterable[str]):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def discover_jsonl(path: str | Path) -> list[Path]:
    path = Path(path)
    if path.is_file():
        return [path]
    if not path.exists():
        raise FileNotFoundError(path)
    return sorted(candidate for candidate in path.rglob("*.jsonl") if candidate.is_file())


def load_records(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for source in discover_jsonl(path):
        with source.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, 1):
                if not raw_line.strip():
                    continue
                try:
                    value = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    errors.append(f"{source}:{line_number}: invalid JSON: {exc.msg}")
                    continue
                if not isinstance(value, dict):
                    errors.append(f"{source}:{line_number}: record must be a JSON object")
                    continue
                value["_source"] = f"{source}:{line_number}"
                records.append(value)
    if errors:
        raise ValidationError(errors)
    return records


def load_source_registry_ids(path: str | Path) -> set[str]:
    """Read source IDs from the intentionally simple top-level YAML registry."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    ids: set[str] = set()
    in_sources = False
    pattern = re.compile(r"^\s{2}- id:\s*([a-z0-9][a-z0-9_-]*)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "sources:":
            in_sources = True
            continue
        if line == "required_source_gaps:":
            break
        if in_sources and (match := pattern.match(line)):
            ids.add(match.group(1))
    if not ids:
        raise ValidationError([f"{path}: no source IDs found in sources section"])
    return ids


def _walk_strings(value: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_strings(child, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, child in value.items():
            if key != "_source":
                yield from _walk_strings(child, f"{path}.{key}")


def _object(
    value: Any,
    label: str,
    errors: list[str],
    *,
    required: set[str],
    optional: set[str] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{label}: must be an object")
        return None
    allowed = required | (optional or set())
    missing = required - set(value)
    unknown = set(value) - allowed
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(sorted(missing))}")
    if unknown:
        errors.append(f"{label}: unknown fields: {', '.join(sorted(unknown))}")
    return value


def _nonempty_string(value: Any, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label}: non-empty string required")
        return None
    return value


def _list_of_strings(value: Any, label: str, errors: list[str], *, min_items: int = 0) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        errors.append(f"{label}: must be an array of non-empty strings")
        return []
    if len(value) < min_items:
        errors.append(f"{label}: at least {min_items} value(s) required")
    if len(value) != len(set(value)):
        errors.append(f"{label}: duplicate values are not allowed")
    return value


def _date_time(value: Any, label: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str):
        errors.append(f"{label}: RFC 3339 date-time with timezone required")
        return None
    # JSON Schema date-time is RFC 3339: the T, seconds, and UTC designator or
    # numeric offset are mandatory. Keeping the runtime validator equivalent
    # avoids naive/aware comparison errors after otherwise permissive parsing.
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
        value,
    ):
        errors.append(f"{label}: RFC 3339 date-time with timezone required")
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        errors.append(f"{label}: invalid RFC 3339 date-time")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(f"{label}: RFC 3339 date-time with timezone required")
        return None
    return parsed


def _date(value: Any, label: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{label}: ISO date string required")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label}: invalid ISO date")
        return None


def _source_id(
    value: Any,
    label: str,
    errors: list[str],
    source_registry_ids: set[str] | None,
) -> None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label}: non-empty source ID required")
    elif source_registry_ids is not None and value not in source_registry_ids:
        errors.append(f"{label}: unknown source registry ID {value!r}")


def _validate_record(
    record: dict[str, Any], label: str, source_registry_ids: set[str] | None
) -> list[str]:
    errors: list[str] = []
    missing = TOP_LEVEL_REQUIRED - set(record)
    unknown = set(record) - ALLOWED_TOP_LEVEL - {"_source"}
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(sorted(missing))}")
    if unknown:
        errors.append(f"{label}: unknown top-level fields: {', '.join(sorted(unknown))}")
    if missing:
        return errors

    if record.get("schema_version") != 1:
        errors.append(f"{label}.schema_version: expected 1")
    record_id = record.get("id")
    if not isinstance(record_id, str) or not ID_RE.fullmatch(record_id):
        errors.append(f"{label}.id: invalid stable ID")
    record_type = record.get("record_type")
    if not isinstance(record_type, str) or record_type not in RECORD_TYPES:
        errors.append(f"{label}.record_type: invalid record type")
    if isinstance(record_id, str) and ID_RE.fullmatch(record_id) and isinstance(record_type, str):
        if record_id.split(".")[1] != record_type:
            errors.append(f"{label}.id: ID type and record_type disagree")
    revision = record.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        errors.append(f"{label}.revision: must be an integer >= 1")
    status = record.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        errors.append(f"{label}.status: invalid status")
    level = record.get("level")
    if not isinstance(level, str) or level not in LEVELS:
        errors.append(f"{label}.level: invalid project level")

    forms = _object(
        record.get("forms"),
        f"{label}.forms",
        errors,
        required={"english", "judeo_algonquin"},
    )
    if forms is not None:
        _list_of_strings(forms.get("english"), f"{label}.forms.english", errors, min_items=1)
        conlang = _object(
            forms.get("judeo_algonquin"),
            f"{label}.forms.judeo_algonquin",
            errors,
            required={"hebrew_script", "romanization"},
            optional={"unpointed", "segmentation", "morpheme_gloss", "variants"},
        )
        if conlang is not None:
            hebrew = _nonempty_string(
                conlang.get("hebrew_script"),
                f"{label}.forms.judeo_algonquin.hebrew_script",
                errors,
            )
            _nonempty_string(
                conlang.get("romanization"),
                f"{label}.forms.judeo_algonquin.romanization",
                errors,
            )
            for key in ("segmentation", "morpheme_gloss"):
                if key in conlang and not isinstance(conlang[key], str):
                    errors.append(f"{label}.forms.judeo_algonquin.{key}: must be a string")
            if "variants" in conlang:
                _list_of_strings(
                    conlang["variants"], f"{label}.forms.judeo_algonquin.variants", errors
                )
            unpointed = conlang.get("unpointed")
            if unpointed is not None and not isinstance(unpointed, str):
                errors.append(f"{label}.forms.judeo_algonquin.unpointed: must be a string")
            elif hebrew is not None and isinstance(unpointed, str):
                if normalize_search(unpointed) != normalize_search(strip_hebrew_marks(hebrew)):
                    errors.append(
                        f"{label}.forms.judeo_algonquin.unpointed: does not match pointed form"
                    )

    senses = record.get("senses")
    if not isinstance(senses, list) or not senses:
        errors.append(f"{label}.senses: at least one sense object required")
    else:
        for index, sense_value in enumerate(senses):
            sense_label = f"{label}.senses[{index}]"
            sense = _object(
                sense_value,
                sense_label,
                errors,
                required={"id", "glosses", "definition", "part_of_speech"},
            )
            if sense is None:
                continue
            sense_id = sense.get("id")
            if not isinstance(sense_id, str) or not SENSE_ID_RE.fullmatch(sense_id):
                errors.append(f"{sense_label}.id: invalid stable sense ID")
            elif isinstance(record_id, str) and not sense_id.startswith(record_id + ".sense."):
                errors.append(f"{sense_label}.id: must be namespaced under record ID")
            _list_of_strings(sense.get("glosses"), f"{sense_label}.glosses", errors, min_items=1)
            _nonempty_string(sense.get("definition"), f"{sense_label}.definition", errors)
            _nonempty_string(
                sense.get("part_of_speech"), f"{sense_label}.part_of_speech", errors
            )

    _list_of_strings(
        record.get("grammatical_features"), f"{label}.grammatical_features", errors
    )

    notes = _object(
        record.get("notes"), f"{label}.notes", errors, required=NOTE_KEYS
    )
    if notes is not None:
        for key in NOTE_KEYS:
            _list_of_strings(notes.get(key), f"{label}.notes.{key}", errors)

    formation = _object(
        record.get("formation"),
        f"{label}.formation",
        errors,
        required={"historical_etymology", "formation_process", "design_alignment"},
    )
    if formation is not None:
        etymologies = formation.get("historical_etymology")
        if not isinstance(etymologies, list):
            errors.append(f"{label}.formation.historical_etymology: must be an array")
        else:
            for index, claim_value in enumerate(etymologies):
                claim_label = f"{label}.formation.historical_etymology[{index}]"
                claim = _object(
                    claim_value,
                    claim_label,
                    errors,
                    required={"claim", "source_ids", "locator", "confidence"},
                )
                if claim is None:
                    continue
                _nonempty_string(claim.get("claim"), f"{claim_label}.claim", errors)
                source_ids = _list_of_strings(
                    claim.get("source_ids"), f"{claim_label}.source_ids", errors, min_items=1
                )
                for index2, value in enumerate(source_ids):
                    _source_id(
                        value,
                        f"{claim_label}.source_ids[{index2}]",
                        errors,
                        source_registry_ids,
                    )
                _nonempty_string(claim.get("locator"), f"{claim_label}.locator", errors)
                if not isinstance(claim.get("confidence"), str) or claim.get(
                    "confidence"
                ) not in {"low", "medium", "high"}:
                    errors.append(f"{claim_label}.confidence: invalid confidence")
        for key in ("formation_process", "design_alignment"):
            if not isinstance(formation.get(key), str):
                errors.append(f"{label}.formation.{key}: must be a string")

    evidence = record.get("source_evidence")
    if not isinstance(evidence, list):
        errors.append(f"{label}.source_evidence: must be an array")
    else:
        evidence_fields = {
            "source_id",
            "language",
            "lect",
            "source_form",
            "source_meaning",
            "grammatical_information",
            "locator",
            "contributor_or_speaker",
            "license_status",
            "accessed_at",
            "confidence",
            "uncertainty",
        }
        for index, item_value in enumerate(evidence):
            item_label = f"{label}.source_evidence[{index}]"
            item = _object(item_value, item_label, errors, required=evidence_fields)
            if item is None:
                continue
            _source_id(item.get("source_id"), f"{item_label}.source_id", errors, source_registry_ids)
            for key in (
                "language",
                "source_form",
                "source_meaning",
                "locator",
                "license_status",
            ):
                _nonempty_string(item.get(key), f"{item_label}.{key}", errors)
            if not isinstance(item.get("lect"), str):
                errors.append(f"{item_label}.lect: must be a string")
            if not isinstance(item.get("grammatical_information"), str):
                errors.append(f"{item_label}.grammatical_information: must be a string")
            if not isinstance(item.get("contributor_or_speaker"), str):
                errors.append(f"{item_label}.contributor_or_speaker: must be a string")
            if not isinstance(item.get("confidence"), str) or item.get(
                "confidence"
            ) not in {"low", "medium", "high", "unknown"}:
                errors.append(f"{item_label}.confidence: invalid confidence")
            if not isinstance(item.get("uncertainty"), str):
                errors.append(f"{item_label}.uncertainty: must be a string")
            _date(item.get("accessed_at"), f"{item_label}.accessed_at", errors)

    provenance = _object(
        record.get("provenance"),
        f"{label}.provenance",
        errors,
        required={"creator_type", "source_ids"},
        optional={"generation_note"},
    )
    if provenance is not None:
        if not isinstance(provenance.get("creator_type"), str) or provenance.get(
            "creator_type"
        ) not in {"human", "model", "legacy_import", "mixed"}:
            errors.append(f"{label}.provenance.creator_type: invalid value")
        source_ids = _list_of_strings(
            provenance.get("source_ids"), f"{label}.provenance.source_ids", errors
        )
        for index, value in enumerate(source_ids):
            _source_id(
                value,
                f"{label}.provenance.source_ids[{index}]",
                errors,
                source_registry_ids,
            )
        if "generation_note" in provenance and not isinstance(
            provenance.get("generation_note"), str
        ):
            errors.append(f"{label}.provenance.generation_note: must be a string")

    relations = _object(
        record.get("relations"), f"{label}.relations", errors, required=RELATION_KEYS
    )
    if relations is not None:
        for key in RELATION_KEYS:
            values = _list_of_strings(relations.get(key), f"{label}.relations.{key}", errors)
            for related_id in values:
                if not ID_RE.fullmatch(related_id):
                    errors.append(f"{label}.relations.{key}: invalid ID {related_id!r}")
        if status == "superseded" and not relations.get("superseded_by"):
            errors.append(f"{label}.relations.superseded_by: required for superseded status")

    metadata = _object(
        record.get("metadata"),
        f"{label}.metadata",
        errors,
        required={"registers", "domains", "tags", "creative_anchor"},
    )
    if metadata is not None:
        for key in ("registers", "domains", "tags"):
            _list_of_strings(metadata.get(key), f"{label}.metadata.{key}", errors)
        anchor = metadata.get("creative_anchor")
        if anchor is not None and not isinstance(anchor, str):
            errors.append(f"{label}.metadata.creative_anchor: must be a string or null")

    narrative = record.get("narrative_analysis")
    if narrative is not None:
        narrative_obj = _object(
            narrative,
            f"{label}.narrative_analysis",
            errors,
            required={"clauses", "transition"},
        )
        if narrative_obj is not None:
            clauses = narrative_obj.get("clauses")
            if not isinstance(clauses, list) or not clauses:
                errors.append(f"{label}.narrative_analysis.clauses: non-empty array required")
            else:
                for index, clause_value in enumerate(clauses):
                    clause_label = f"{label}.narrative_analysis.clauses[{index}]"
                    clause = _object(
                        clause_value,
                        clause_label,
                        errors,
                        required={
                            "clause_id",
                            "construction_ids",
                            "event_role",
                            "participants",
                            "center_shift",
                        },
                    )
                    if clause is None:
                        continue
                    _nonempty_string(clause.get("clause_id"), f"{clause_label}.clause_id", errors)
                    constructions = _list_of_strings(
                        clause.get("construction_ids"),
                        f"{clause_label}.construction_ids",
                        errors,
                    )
                    for construction_id in constructions:
                        if not ID_RE.fullmatch(construction_id) or ".construction." not in construction_id:
                            errors.append(
                                f"{clause_label}.construction_ids: invalid construction ID {construction_id!r}"
                            )
                    if not isinstance(clause.get("event_role"), str) or clause.get(
                        "event_role"
                    ) not in {
                        "foreground",
                        "background",
                        "consequence",
                        "habitual",
                        "standing_pattern",
                        "dialogue",
                        "other",
                    }:
                        errors.append(f"{clause_label}.event_role: invalid value")
                    participants = clause.get("participants")
                    if not isinstance(participants, list):
                        errors.append(f"{clause_label}.participants: must be an array")
                    else:
                        for index2, participant_value in enumerate(participants):
                            participant_label = f"{clause_label}.participants[{index2}]"
                            participant = _object(
                                participant_value,
                                participant_label,
                                errors,
                                required={"participant_id", "discourse_status"},
                            )
                            if participant is None:
                                continue
                            _nonempty_string(
                                participant.get("participant_id"),
                                f"{participant_label}.participant_id",
                                errors,
                            )
                            if not isinstance(
                                participant.get("discourse_status"), str
                            ) or participant.get("discourse_status") not in {
                                "proximate",
                                "obviative",
                                "overt",
                                "unspecified",
                            }:
                                errors.append(
                                    f"{participant_label}.discourse_status: invalid value"
                                )
                    if not isinstance(clause.get("center_shift"), bool):
                        errors.append(f"{clause_label}.center_shift: must be boolean")
            if narrative_obj.get("transition") is not None and not isinstance(
                narrative_obj.get("transition"), str
            ):
                errors.append(f"{label}.narrative_analysis.transition: string or null required")

    review = record.get("review")
    if isinstance(status, str) and status in REVIEWED_STATUSES:
        review_obj = _object(
            review,
            f"{label}.review",
            errors,
            required={"reviewer_type", "decision", "reviewed_at", "note"},
        )
        if review_obj is not None:
            if review_obj.get("decision") != status:
                errors.append(f"{label}.review.decision: must match record status")
            if review_obj.get("reviewer_type") != "human":
                errors.append(
                    f"{label}.review.reviewer_type: lifecycle review must be human"
                )
            _date_time(review_obj.get("reviewed_at"), f"{label}.review.reviewed_at", errors)
            if not isinstance(review_obj.get("note"), str):
                errors.append(f"{label}.review.note: must be a string")
    elif review is not None:
        errors.append(f"{label}.review: not allowed before a reviewed lifecycle decision")

    created = _date_time(record.get("created_at"), f"{label}.created_at", errors)
    updated = _date_time(record.get("updated_at"), f"{label}.updated_at", errors)
    if created is not None and updated is not None and updated < created:
        errors.append(f"{label}.updated_at: cannot precede created_at")
    _nonempty_string(record.get("change_note"), f"{label}.change_note", errors)

    for string_path, text in _walk_strings(record, label):
        if not is_nfc(text):
            errors.append(f"{string_path}: text is not NFC-normalized")
        unsafe = unsafe_codepoints(text)
        if unsafe:
            errors.append(f"{string_path}: unsafe code points: {', '.join(unsafe)}")
    return errors


def validate_records(
    records: list[dict[str, Any]], *, source_registry_ids: set[str] | None = None
) -> list[dict[str, Any]]:
    errors: list[str] = []
    ids: dict[str, str] = {}
    sense_ids: dict[str, str] = {}
    headwords: dict[str, str] = {}

    for index, record in enumerate(records):
        label = record.get("_source", f"record[{index}]")
        errors.extend(_validate_record(record, label, source_registry_ids))
        record_id = record.get("id")
        if isinstance(record_id, str):
            if record_id in ids:
                errors.append(f"{label}.id: duplicate of {ids[record_id]}")
            else:
                ids[record_id] = label
        senses = record.get("senses")
        if isinstance(senses, list):
            for sense in senses:
                sense_id = sense.get("id") if isinstance(sense, dict) else None
                if isinstance(sense_id, str):
                    if sense_id in sense_ids:
                        errors.append(f"{label}: duplicate sense ID from {sense_ids[sense_id]}")
                    else:
                        sense_ids[sense_id] = label
        if record.get("record_type") in {"lexeme", "morpheme"}:
            forms = record.get("forms")
            conlang = forms.get("judeo_algonquin") if isinstance(forms, dict) else None
            headword = conlang.get("hebrew_script") if isinstance(conlang, dict) else None
            if isinstance(headword, str):
                normalized = normalize_search(headword)
                metadata = record.get("metadata")
                tags = metadata.get("tags", []) if isinstance(metadata, dict) else []
                if normalized in headwords and "homonym" not in tags:
                    errors.append(
                        f"{label}: duplicate normalized headword; mark an intentional homonym explicitly"
                    )
                else:
                    headwords[normalized] = label

    known_ids = set(ids)
    status_by_id = {
        record_id: record.get("status")
        for record in records
        if isinstance((record_id := record.get("id")), str)
    }
    for index, record in enumerate(records):
        label = record.get("_source", f"record[{index}]")
        relations = record.get("relations")
        if isinstance(relations, dict):
            for relation, related_ids in relations.items():
                if not isinstance(related_ids, list):
                    continue
                for related_id in related_ids:
                    if isinstance(related_id, str) and related_id not in known_ids:
                        errors.append(f"{label}.relations.{relation}: unknown ID {related_id}")
        narrative = record.get("narrative_analysis")
        if isinstance(narrative, dict):
            for clause in narrative.get("clauses", []):
                if not isinstance(clause, dict):
                    continue
                for construction_id in clause.get("construction_ids", []):
                    if isinstance(construction_id, str) and construction_id not in known_ids:
                        errors.append(
                            f"{label}.narrative_analysis: unknown construction ID {construction_id}"
                        )
        if record.get("status") == "canonical" and isinstance(relations, dict):
            for dependency in relations.get("depends_on", []):
                if status_by_id.get(dependency) not in {"reviewed", "canonical"}:
                    errors.append(
                        f"{label}.relations.depends_on: canonical record depends on unreviewed {dependency}"
                    )

    if errors:
        raise ValidationError(errors)
    for record in records:
        record.pop("_source", None)
    return records


def canonical_json(record: dict[str, Any]) -> str:
    clean = {key: value for key, value in record.items() if key != "_source"}
    return json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
