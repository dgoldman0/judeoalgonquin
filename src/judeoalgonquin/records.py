"""JSONL loading and deterministic project-level validation."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

from .normalize import is_nfc, normalize_search, strip_hebrew_marks, unsafe_codepoints
from .orthography import (
    COMPONENTWISE_PROFILE,
    CONTACT_POINTED_PROFILE,
    HEBREW_RETAINED_PROFILE,
    LEGACY_UNVERIFIED_PROFILE,
    MUNSEE_TRANSPORT_PROFILE,
    PROJECT_SCHEMATIC_PROFILE,
    assert_transport_round_trip,
    assert_contact_round_trip,
)


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
REGISTER_LABELS = {"ordinary", "careful", "narrative", "literary", "ritual_style"}
RELATION_KEYS = {
    "depends_on",
    "related_to",
    "conflicts_with",
    "supersedes",
    "superseded_by",
}
RELATION_REQUIRED = RELATION_KEYS | {"dependency_revisions"}
NOTE_KEYS = {"translation", "grammar", "design"}
FORMATION_KINDS = {
    "direct_borrowing",
    "phonological_adaptation",
    "orthographic_adaptation",
    "calque",
    "blend",
    "compound",
    "derivation",
    "semantic_reallocation",
    "semantic_extension",
    "new_coinage",
    "mixed",
}
FORMATION_OPERATIONS = {
    "retain",
    "transliterate",
    "phonological_adaptation",
    "orthographic_adaptation",
    "combine",
    "derive",
    "calque",
    "semantic_reallocation",
    "semantic_extension",
    "regularize",
    "other",
}
SOURCE_USE_TYPES = {
    "lexical",
    "grammatical",
    "historical",
    "orthographic",
    "cultural_context",
    "comparative",
}
CANON_BLOCKING_TAGS = {"candidate", "noncanonical", "unverified"}
CANON_SOURCE_GAP_TAGS = {
    "munsee-derived": "munsee_current_community_lexical_guidance",
    "mahican-derived": "mahican_normative_reference",
    "wayyiqtol-derived": "biblical_hebrew_grammar",
    "weqatal-derived": "biblical_hebrew_grammar",
}
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
    "composition",
    "construction_spec",
    "paradigm",
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
    return set(load_source_registry(path))


def load_source_registry(path: str | Path) -> dict[str, dict[str, str]]:
    """Read the source-policy scalars needed for deterministic validation.

    The registry deliberately uses a constrained YAML layout. Parsing only the
    top-level scalar fields of each source keeps the validator dependency-free;
    lists and descriptive nested blocks remain documentation-only.
    """

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    sources: dict[str, dict[str, str]] = {}
    in_sources = False
    current: dict[str, str] | None = None
    id_pattern = re.compile(r"^\s{2}- id:\s*([a-z0-9][a-z0-9_-]*)\s*$")
    scalar_pattern = re.compile(r"^\s{4}([a-z][a-z0-9_]*):\s*(.*?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "sources:":
            in_sources = True
            continue
        if line == "required_source_gaps:":
            break
        if not in_sources:
            continue
        if match := id_pattern.match(line):
            source_id = match.group(1)
            current = {"id": source_id}
            sources[source_id] = current
            continue
        if current is not None and (match := scalar_pattern.match(line)):
            key, raw_value = match.groups()
            if raw_value and raw_value not in {">-", "|", "|-"}:
                if raw_value.startswith(('"', "'")) and raw_value.endswith(
                    ('"', "'")
                ):
                    raw_value = raw_value[1:-1]
                current[key] = raw_value
    if not sources:
        raise ValidationError([f"{path}: no source IDs found in sources section"])
    return sources


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


def _string_map(value: Any, label: str, errors: list[str], *, min_items: int = 0) -> dict[str, str]:
    if not isinstance(value, dict) or any(
        not isinstance(key, str)
        or not key
        or not isinstance(item, str)
        or not item
        for key, item in value.items()
    ):
        errors.append(f"{label}: must be an object of non-empty string keys and values")
        return {}
    if len(value) < min_items:
        errors.append(f"{label}: at least {min_items} value(s) required")
    return value


def _contiguous_orders(values: list[Any], label: str, errors: list[str]) -> None:
    orders = [item.get("order") for item in values if isinstance(item, dict)]
    if any(not isinstance(order, int) or isinstance(order, bool) or order < 1 for order in orders):
        errors.append(f"{label}: every order must be an integer >= 1")
    elif sorted(orders) != list(range(1, len(values) + 1)):
        errors.append(f"{label}: orders must be unique and contiguous from 1")


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
    record: dict[str, Any],
    label: str,
    source_registry_ids: set[str] | None,
    source_registry: dict[str, dict[str, str]] | None = None,
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

    conlang: dict[str, Any] | None = None
    orthography: dict[str, Any] | None = None
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
            required={"hebrew_script", "romanization", "orthography"},
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
            orthography = _object(
                conlang.get("orthography"),
                f"{label}.forms.judeo_algonquin.orthography",
                errors,
                required={
                    "status",
                    "profile_id",
                    "script_origin",
                    "input_system",
                    "input_level",
                    "source_exact",
                    "normalized_input",
                    "reversibility",
                },
            )
            if orthography is not None:
                orthography_label = f"{label}.forms.judeo_algonquin.orthography"
                status_value = orthography.get("status")
                if status_value not in {
                    "source_retained",
                    "provisional_transport",
                    "contact_adapted",
                    "componentwise",
                    "project_schematic",
                    "unverified",
                }:
                    errors.append(f"{orthography_label}.status: invalid value")
                profile_id = _nonempty_string(
                    orthography.get("profile_id"), f"{orthography_label}.profile_id", errors
                )
                if orthography.get("script_origin") not in {
                    "retained_hebrew",
                    "munsee_source_transport",
                    "contact_adapted",
                    "componentwise",
                    "project_schematic",
                    "legacy_unverified",
                }:
                    errors.append(f"{orthography_label}.script_origin: invalid value")
                _nonempty_string(
                    orthography.get("input_system"),
                    f"{orthography_label}.input_system",
                    errors,
                )
                if orthography.get("input_level") not in {
                    "source_hebrew",
                    "citation",
                    "surface",
                    "morphophonemic",
                    "contact_phonemic",
                    "componentwise",
                    "schematic",
                    "unverified",
                }:
                    errors.append(f"{orthography_label}.input_level: invalid value")
                if not isinstance(orthography.get("source_exact"), str):
                    errors.append(f"{orthography_label}.source_exact: must be a string")
                normalized_input = _nonempty_string(
                    orthography.get("normalized_input"),
                    f"{orthography_label}.normalized_input",
                    errors,
                )
                if orthography.get("reversibility") not in {
                    "not_transduced",
                    "pointed_only",
                    "componentwise",
                    "unverified",
                }:
                    errors.append(f"{orthography_label}.reversibility: invalid value")
                profile_contracts = {
                    "source_retained": (
                        HEBREW_RETAINED_PROFILE,
                        "retained_hebrew",
                        "source_hebrew",
                        "not_transduced",
                    ),
                    "provisional_transport": (
                        MUNSEE_TRANSPORT_PROFILE,
                        "munsee_source_transport",
                        None,
                        "pointed_only",
                    ),
                    "contact_adapted": (
                        CONTACT_POINTED_PROFILE,
                        "contact_adapted",
                        "contact_phonemic",
                        "pointed_only",
                    ),
                    "componentwise": (
                        COMPONENTWISE_PROFILE,
                        "componentwise",
                        "componentwise",
                        "componentwise",
                    ),
                    "project_schematic": (
                        PROJECT_SCHEMATIC_PROFILE,
                        "project_schematic",
                        "schematic",
                        "not_transduced",
                    ),
                    "unverified": (
                        LEGACY_UNVERIFIED_PROFILE,
                        "legacy_unverified",
                        "unverified",
                        "unverified",
                    ),
                }
                contract = profile_contracts.get(status_value)
                if contract is not None:
                    expected_profile, expected_origin, expected_level, expected_reversibility = contract
                    if profile_id != expected_profile:
                        errors.append(f"{orthography_label}.profile_id: does not match status")
                    if orthography.get("script_origin") != expected_origin:
                        errors.append(f"{orthography_label}.script_origin: does not match status")
                    if expected_level is not None and orthography.get("input_level") != expected_level:
                        errors.append(f"{orthography_label}.input_level: does not match status")
                    if orthography.get("reversibility") != expected_reversibility:
                        errors.append(f"{orthography_label}.reversibility: does not match status")

                if status_value == "provisional_transport":
                    if orthography.get("input_level") not in {
                        "citation",
                        "surface",
                        "morphophonemic",
                    }:
                        errors.append(
                            f"{orthography_label}.input_level: invalid for provisional transport"
                        )
                    _nonempty_string(
                        orthography.get("source_exact"),
                        f"{orthography_label}.source_exact",
                        errors,
                    )
                    if normalized_input is not None and conlang.get("romanization") != normalized_input:
                        errors.append(
                            f"{orthography_label}.normalized_input: must equal transport romanization"
                        )
                    if normalized_input is not None and hebrew is not None:
                        try:
                            encoded = assert_transport_round_trip(normalized_input)
                        except ValueError as exc:
                            errors.append(f"{orthography_label}: {exc}")
                        else:
                            if encoded != hebrew:
                                errors.append(
                                    f"{orthography_label}: Hebrew form does not match transport profile"
                                )
                elif status_value == "contact_adapted":
                    if normalized_input is not None and conlang.get("romanization") != normalized_input:
                        errors.append(
                            f"{orthography_label}.normalized_input: must equal contact romanization"
                        )
                    if normalized_input is not None and hebrew is not None:
                        try:
                            encoded = assert_contact_round_trip(normalized_input)
                        except ValueError as exc:
                            errors.append(f"{orthography_label}: {exc}")
                        else:
                            if encoded != hebrew:
                                errors.append(
                                    f"{orthography_label}: Hebrew form does not match contact profile"
                                )
                elif status_value == "source_retained":
                    if hebrew is not None and orthography.get("source_exact") != hebrew:
                        errors.append(
                            f"{orthography_label}.source_exact: must equal retained Hebrew form"
                        )
                elif status_value in {"componentwise", "project_schematic", "unverified"}:
                    if normalized_input is not None and conlang.get("romanization") != normalized_input:
                        errors.append(
                            f"{orthography_label}.normalized_input: must equal record romanization"
                        )
                    if (
                        status_value == "componentwise"
                        and {"contact-clause", "contact-phrase"}.intersection(
                            record.get("metadata", {}).get("tags", [])
                        )
                        and normalized_input is not None
                        and hebrew is not None
                    ):
                        try:
                            encoded = assert_contact_round_trip(normalized_input)
                        except ValueError as exc:
                            errors.append(f"{orthography_label}: {exc}")
                        else:
                            if encoded != hebrew:
                                errors.append(
                                    f"{orthography_label}: Hebrew form does not match "
                                    "componentwise contact encoding"
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
                required={"id", "glosses", "definition", "part_of_speech", "translations"},
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
            translations = _object(
                sense.get("translations"),
                f"{sense_label}.translations",
                errors,
                required={"literal", "idiomatic"},
            )
            if translations is not None:
                _list_of_strings(
                    translations.get("literal"),
                    f"{sense_label}.translations.literal",
                    errors,
                    min_items=1 if record_type in {"phrase", "sentence", "paragraph"} else 0,
                )
                _list_of_strings(
                    translations.get("idiomatic"),
                    f"{sense_label}.translations.idiomatic",
                    errors,
                    min_items=1,
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
        required={
            "historical_etymology",
            "formation_kind",
            "inputs",
            "operations",
            "formation_process",
            "design_alignment",
        },
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
        formation_kind = formation.get("formation_kind")
        if not isinstance(formation_kind, str) or formation_kind not in FORMATION_KINDS:
            errors.append(f"{label}.formation.formation_kind: invalid value")
        inputs = formation.get("inputs")
        if not isinstance(inputs, list):
            errors.append(f"{label}.formation.inputs: must be an array")
        else:
            for index, input_value in enumerate(inputs):
                input_label = f"{label}.formation.inputs[{index}]"
                formation_input = _object(
                    input_value,
                    input_label,
                    errors,
                    required={"input_type", "input_id", "form", "contribution"},
                )
                if formation_input is None:
                    continue
                input_type = formation_input.get("input_type")
                if input_type not in {"source_record", "language_record", "project_design"}:
                    errors.append(f"{input_label}.input_type: invalid value")
                input_id = _nonempty_string(
                    formation_input.get("input_id"), f"{input_label}.input_id", errors
                )
                if input_id is not None and input_type == "source_record":
                    _source_id(
                        input_id,
                        f"{input_label}.input_id",
                        errors,
                        source_registry_ids,
                    )
                elif input_id is not None and input_type == "language_record":
                    if not ID_RE.fullmatch(input_id):
                        errors.append(f"{input_label}.input_id: invalid language record ID")
                if not isinstance(formation_input.get("form"), str):
                    errors.append(f"{input_label}.form: must be a string")
                _nonempty_string(
                    formation_input.get("contribution"),
                    f"{input_label}.contribution",
                    errors,
                )
        operations = formation.get("operations")
        if not isinstance(operations, list):
            errors.append(f"{label}.formation.operations: must be an array")
        else:
            _contiguous_orders(operations, f"{label}.formation.operations", errors)
            for index, operation_value in enumerate(operations):
                operation_label = f"{label}.formation.operations[{index}]"
                operation = _object(
                    operation_value,
                    operation_label,
                    errors,
                    required={"order", "operation", "description"},
                )
                if operation is None:
                    continue
                if operation.get("operation") not in FORMATION_OPERATIONS:
                    errors.append(f"{operation_label}.operation: invalid value")
                _nonempty_string(
                    operation.get("description"),
                    f"{operation_label}.description",
                    errors,
                )
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
            "supports_sense_ids",
            "use_type",
            "gap_reason",
        }
        record_sense_ids = {
            sense.get("id")
            for sense in (senses if isinstance(senses, list) else [])
            if isinstance(sense, dict) and isinstance(sense.get("id"), str)
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
            supported_senses = _list_of_strings(
                item.get("supports_sense_ids"),
                f"{item_label}.supports_sense_ids",
                errors,
                min_items=1,
            )
            for sense_id in supported_senses:
                if sense_id not in record_sense_ids:
                    errors.append(
                        f"{item_label}.supports_sense_ids: unknown sense ID {sense_id!r}"
                    )
            use_type = item.get("use_type")
            if not isinstance(use_type, str) or use_type not in SOURCE_USE_TYPES:
                errors.append(f"{item_label}.use_type: invalid value")
            gap_reason = item.get("gap_reason")
            if gap_reason is not None and not isinstance(gap_reason, str):
                errors.append(f"{item_label}.gap_reason: must be a string or null")
            source_id = item.get("source_id")
            if source_registry is not None and isinstance(source_id, str):
                policy = source_registry.get(source_id)
                if policy is not None:
                    lexical_import = policy.get("lexical_import")
                    if use_type in {"lexical", "grammatical", "orthographic"}:
                        if lexical_import == "not_from_this_page":
                            errors.append(
                                f"{item_label}: registry forbids lexical or grammatical import from this source"
                            )
                        if (
                            lexical_import == "documented_gap_and_review_required"
                            and not gap_reason
                        ):
                            errors.append(
                                f"{item_label}.gap_reason: required by broader-source policy"
                            )
                    registry_license = policy.get("license_status")
                    if registry_license and item.get("license_status") != registry_license:
                        errors.append(
                            f"{item_label}.license_status: must match registry value {registry_license!r}"
                        )
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
        used_source_ids = {
            item.get("source_id")
            for item in (evidence if isinstance(evidence, list) else [])
            if isinstance(item, dict) and isinstance(item.get("source_id"), str)
        }
        if isinstance(formation, dict):
            used_source_ids.update(
                item.get("input_id")
                for item in formation.get("inputs", [])
                if isinstance(item, dict)
                and item.get("input_type") == "source_record"
                and isinstance(item.get("input_id"), str)
            )
        if set(source_ids) != used_source_ids:
            errors.append(
                f"{label}.provenance.source_ids: must exactly match cited source inputs and evidence"
            )

    relations = _object(
        record.get("relations"), f"{label}.relations", errors, required=RELATION_REQUIRED
    )
    if relations is not None:
        for key in RELATION_KEYS:
            values = _list_of_strings(relations.get(key), f"{label}.relations.{key}", errors)
            for related_id in values:
                if not ID_RE.fullmatch(related_id):
                    errors.append(f"{label}.relations.{key}: invalid ID {related_id!r}")
        if status == "superseded" and not relations.get("superseded_by"):
            errors.append(f"{label}.relations.superseded_by: required for superseded status")
        dependency_revisions = relations.get("dependency_revisions")
        if not isinstance(dependency_revisions, dict):
            errors.append(f"{label}.relations.dependency_revisions: must be an object")
        else:
            for dependency_id, dependency_revision in dependency_revisions.items():
                if not isinstance(dependency_id, str) or not ID_RE.fullmatch(dependency_id):
                    errors.append(
                        f"{label}.relations.dependency_revisions: invalid ID {dependency_id!r}"
                    )
                if (
                    not isinstance(dependency_revision, int)
                    or isinstance(dependency_revision, bool)
                    or dependency_revision < 1
                ):
                    errors.append(
                        f"{label}.relations.dependency_revisions.{dependency_id}: integer >= 1 required"
                    )
            if set(dependency_revisions) != set(relations.get("depends_on", [])):
                errors.append(
                    f"{label}.relations.dependency_revisions: keys must exactly match depends_on"
                )

    composition = record.get("composition")
    if record_type in {"phrase", "sentence", "paragraph"} and composition is None:
        errors.append(f"{label}.composition: required for {record_type} records")
    if composition is not None:
        composition_obj = _object(
            composition,
            f"{label}.composition",
            errors,
            required={"components", "construction_ids"},
        )
        if composition_obj is not None:
            components = composition_obj.get("components")
            if not isinstance(components, list) or not components:
                errors.append(f"{label}.composition.components: non-empty array required")
            else:
                _contiguous_orders(components, f"{label}.composition.components", errors)
                for index, component_value in enumerate(components):
                    component_label = f"{label}.composition.components[{index}]"
                    component = _object(
                        component_value,
                        component_label,
                        errors,
                        required={
                            "order",
                            "record_id",
                            "record_revision",
                            "sense_id",
                            "role",
                            "realization",
                        },
                    )
                    if component is None:
                        continue
                    dependency_id = component.get("record_id")
                    if not isinstance(dependency_id, str) or not ID_RE.fullmatch(dependency_id):
                        errors.append(f"{component_label}.record_id: invalid record ID")
                    dependency_revision = component.get("record_revision")
                    if (
                        not isinstance(dependency_revision, int)
                        or isinstance(dependency_revision, bool)
                        or dependency_revision < 1
                    ):
                        errors.append(f"{component_label}.record_revision: integer >= 1 required")
                    sense_id = component.get("sense_id")
                    if not isinstance(sense_id, str) or not SENSE_ID_RE.fullmatch(sense_id):
                        errors.append(f"{component_label}.sense_id: invalid sense ID")
                    _nonempty_string(component.get("role"), f"{component_label}.role", errors)
                    _nonempty_string(
                        component.get("realization"),
                        f"{component_label}.realization",
                        errors,
                    )
            construction_ids = _list_of_strings(
                composition_obj.get("construction_ids"),
                f"{label}.composition.construction_ids",
                errors,
            )
            for construction_id in construction_ids:
                if not ID_RE.fullmatch(construction_id) or ".construction." not in construction_id:
                    errors.append(
                        f"{label}.composition.construction_ids: invalid construction ID {construction_id!r}"
                    )
            if isinstance(conlang, dict):
                segmentation = conlang.get("segmentation")
                morpheme_gloss = conlang.get("morpheme_gloss")
                if not isinstance(segmentation, str) or not segmentation:
                    errors.append(
                        f"{label}.forms.judeo_algonquin.segmentation: required for composition"
                    )
                if not isinstance(morpheme_gloss, str) or not morpheme_gloss:
                    errors.append(
                        f"{label}.forms.judeo_algonquin.morpheme_gloss: required for composition"
                    )
                if (
                    isinstance(segmentation, str)
                    and segmentation
                    and isinstance(morpheme_gloss, str)
                    and morpheme_gloss
                    and len(segmentation.split("-")) != len(morpheme_gloss.split("-"))
                ):
                    errors.append(
                        f"{label}.forms.judeo_algonquin: segmentation and morpheme gloss must align"
                    )
                if (
                    isinstance(components, list)
                    and isinstance(segmentation, str)
                    and segmentation
                    and len(components) != len(segmentation.split("-"))
                ):
                    errors.append(
                        f"{label}.composition.components: count must match segmented units"
                    )

    construction_spec = record.get("construction_spec")
    if record_type == "construction" and construction_spec is None:
        errors.append(f"{label}.construction_spec: required for construction records")
    if construction_spec is not None:
        spec = _object(
            construction_spec,
            f"{label}.construction_spec",
            errors,
            required={
                "kind",
                "function",
                "formalism",
                "host_classes",
                "ordering",
                "allomorphy",
                "restrictions",
                "counterexamples",
                "test_refs",
                "productivity",
            },
        )
        if spec is not None:
            if spec.get("kind") not in {"morphological", "syntactic", "discourse", "orthographic"}:
                errors.append(f"{label}.construction_spec.kind: invalid value")
            for key in ("function", "formalism"):
                _nonempty_string(spec.get(key), f"{label}.construction_spec.{key}", errors)
            for key in (
                "host_classes",
                "ordering",
                "allomorphy",
                "restrictions",
                "counterexamples",
            ):
                _list_of_strings(spec.get(key), f"{label}.construction_spec.{key}", errors)
            test_refs = _list_of_strings(
                spec.get("test_refs"),
                f"{label}.construction_spec.test_refs",
                errors,
                min_items=1,
            )
            if not any("positive" in test_ref for test_ref in test_refs):
                errors.append(
                    f"{label}.construction_spec.test_refs: positive test reference required"
                )
            if not any("negative" in test_ref for test_ref in test_refs):
                errors.append(
                    f"{label}.construction_spec.test_refs: negative test reference required"
                )
            if spec.get("productivity") not in {
                "unproductive",
                "limited",
                "productive_candidate",
                "productive",
            }:
                errors.append(f"{label}.construction_spec.productivity: invalid value")

    paradigm = record.get("paradigm")
    if paradigm is not None:
        paradigm_obj = _object(
            paradigm,
            f"{label}.paradigm",
            errors,
            required={"dimensions", "cells", "gaps"},
        )
        if paradigm_obj is not None:
            dimension_values: dict[str, set[str]] = {}
            dimensions = paradigm_obj.get("dimensions")
            if not isinstance(dimensions, list) or not dimensions:
                errors.append(f"{label}.paradigm.dimensions: non-empty array required")
            else:
                for index, dimension_value in enumerate(dimensions):
                    dimension_label = f"{label}.paradigm.dimensions[{index}]"
                    dimension = _object(
                        dimension_value,
                        dimension_label,
                        errors,
                        required={"name", "values"},
                    )
                    if dimension is None:
                        continue
                    name = _nonempty_string(
                        dimension.get("name"), f"{dimension_label}.name", errors
                    )
                    values = _list_of_strings(
                        dimension.get("values"),
                        f"{dimension_label}.values",
                        errors,
                        min_items=1,
                    )
                    if name is not None:
                        if name in dimension_values:
                            errors.append(f"{dimension_label}.name: duplicate dimension")
                        dimension_values[name] = set(values)
            seen_feature_bundles: set[tuple[tuple[str, str], ...]] = set()
            for group_name in ("cells", "gaps"):
                group = paradigm_obj.get(group_name)
                if not isinstance(group, list):
                    errors.append(f"{label}.paradigm.{group_name}: must be an array")
                    continue
                for index, item_value in enumerate(group):
                    item_label = f"{label}.paradigm.{group_name}[{index}]"
                    required = (
                        {
                            "features",
                            "hebrew_script",
                            "romanization",
                            "segmentation",
                            "morpheme_gloss",
                            "meaning",
                            "status",
                        }
                        if group_name == "cells"
                        else {"features", "reason"}
                    )
                    item = _object(item_value, item_label, errors, required=required)
                    if item is None:
                        continue
                    features = _string_map(
                        item.get("features"), f"{item_label}.features", errors, min_items=1
                    )
                    if dimension_values and set(features) != set(dimension_values):
                        errors.append(
                            f"{item_label}.features: keys must exactly match paradigm dimensions"
                        )
                    for name, value in features.items():
                        if name in dimension_values and value not in dimension_values[name]:
                            errors.append(
                                f"{item_label}.features.{name}: value is outside declared dimension"
                            )
                    bundle = tuple(sorted(features.items()))
                    if bundle in seen_feature_bundles:
                        errors.append(f"{item_label}.features: duplicate paradigm bundle")
                    seen_feature_bundles.add(bundle)
                    if group_name == "cells":
                        for key in ("hebrew_script", "romanization", "meaning"):
                            _nonempty_string(item.get(key), f"{item_label}.{key}", errors)
                        for key in ("segmentation", "morpheme_gloss"):
                            if not isinstance(item.get(key), str):
                                errors.append(f"{item_label}.{key}: must be a string")
                        if item.get("status") not in {
                            "attested_source",
                            "attested_pattern",
                            "adapted_candidate",
                            "reviewed",
                            "canonical",
                        }:
                            errors.append(f"{item_label}.status: invalid value")
                        if (
                            item.get("status") == "adapted_candidate"
                            and "contact-grammar"
                            in record.get("metadata", {}).get("tags", [])
                        ):
                            romanization = item.get("romanization")
                            hebrew_script = item.get("hebrew_script")
                            if isinstance(romanization, str) and isinstance(hebrew_script, str):
                                try:
                                    encoded = assert_contact_round_trip(romanization)
                                except ValueError as exc:
                                    errors.append(f"{item_label}: {exc}")
                                else:
                                    if encoded != hebrew_script:
                                        errors.append(
                                            f"{item_label}.hebrew_script: does not match "
                                            "contact encoding"
                                        )
                    else:
                        _nonempty_string(item.get("reason"), f"{item_label}.reason", errors)

            if status == "canonical" and isinstance(construction_spec, dict):
                if construction_spec.get("productivity") == "productive":
                    expected = 1
                    for values in dimension_values.values():
                        expected *= len(values)
                    if len(seen_feature_bundles) != expected:
                        errors.append(
                            f"{label}.paradigm: productive canonical paradigm has unexplained gaps"
                        )

    metadata = _object(
        record.get("metadata"),
        f"{label}.metadata",
        errors,
        required={"registers", "domains", "tags", "creative_anchor"},
        optional={"lexical_layer"},
    )
    if metadata is not None:
        for key in ("registers", "domains", "tags"):
            _list_of_strings(metadata.get(key), f"{label}.metadata.{key}", errors)
        registers = metadata.get("registers")
        if isinstance(registers, list):
            unknown_registers = sorted(
                value
                for value in registers
                if isinstance(value, str) and value not in REGISTER_LABELS
            )
            if unknown_registers:
                errors.append(
                    f"{label}.metadata.registers: unknown labels {unknown_registers!r}"
                )
        anchor = metadata.get("creative_anchor")
        if anchor is not None and not isinstance(anchor, str):
            errors.append(f"{label}.metadata.creative_anchor: must be a string or null")
        lexical_layer = metadata.get("lexical_layer")
        if lexical_layer is not None and lexical_layer not in {
            "donor_candidate",
            "direct_contact_inheritance",
            "contact_native_formation",
            "learned_literary_reborrowing",
        }:
            errors.append(f"{label}.metadata.lexical_layer: invalid value")
        if (
            record_type in {"lexeme", "morpheme"}
            and isinstance(orthography, dict)
            and orthography.get("status") == "contact_adapted"
            and lexical_layer
            not in {
                "direct_contact_inheritance",
                "contact_native_formation",
                "learned_literary_reborrowing",
            }
        ):
            errors.append(
                f"{label}.metadata.lexical_layer: contact-adapted lexical records "
                "require a contact-language layer"
            )

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
            required={
                "reviewer_type",
                "reviewer_id",
                "authority",
                "decision",
                "reviewed_at",
                "note",
            },
        )
        if review_obj is not None:
            if review_obj.get("decision") != status:
                errors.append(f"{label}.review.decision: must match record status")
            if review_obj.get("reviewer_type") != "human":
                errors.append(
                    f"{label}.review.reviewer_type: lifecycle review must be human"
                )
            _nonempty_string(
                review_obj.get("reviewer_id"), f"{label}.review.reviewer_id", errors
            )
            _nonempty_string(
                review_obj.get("authority"), f"{label}.review.authority", errors
            )
            _date_time(review_obj.get("reviewed_at"), f"{label}.review.reviewed_at", errors)
            if not isinstance(review_obj.get("note"), str):
                errors.append(f"{label}.review.note: must be a string")
    elif review is not None:
        errors.append(f"{label}.review: not allowed before a reviewed lifecycle decision")

    if status == "canonical":
        tags = metadata.get("tags", []) if isinstance(metadata, dict) else []
        lexical_layer = (
            metadata.get("lexical_layer") if isinstance(metadata, dict) else None
        )
        if lexical_layer == "donor_candidate":
            errors.append(
                f"{label}.metadata.lexical_layer: donor candidates cannot be canonical"
            )
        creator_type = provenance.get("creator_type") if isinstance(provenance, dict) else None
        if creator_type == "legacy_import":
            errors.append(f"{label}.provenance.creator_type: legacy imports cannot be canonical")
        blocking_tags = sorted(
            tag
            for tag in tags
            if tag in CANON_BLOCKING_TAGS
            or tag.startswith("provisional-")
            or tag.endswith("-provisional")
        )
        if blocking_tags:
            errors.append(
                f"{label}.metadata.tags: canon-blocking tags remain: "
                + ", ".join(blocking_tags)
            )
        orthography_status = orthography.get("status") if isinstance(orthography, dict) else None
        if orthography_status in {
            "provisional_transport",
            "contact_adapted",
            "project_schematic",
            "unverified",
        }:
            errors.append(
                f"{label}.forms.judeo_algonquin.orthography.status: "
                f"{orthography_status} blocks canon"
            )
        unresolved_gaps = sorted(
            {CANON_SOURCE_GAP_TAGS[tag] for tag in tags if tag in CANON_SOURCE_GAP_TAGS}
        )
        if unresolved_gaps:
            errors.append(
                f"{label}.metadata.tags: unresolved source gaps block canon: "
                + ", ".join(unresolved_gaps)
            )
        source_derived = (
            isinstance(formation, dict)
            and any(
                isinstance(item, dict) and item.get("input_type") == "source_record"
                for item in formation.get("inputs", [])
            )
        )
        if source_derived:
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"{label}.source_evidence: source-derived canon requires evidence")
            else:
                supported = {
                    sense_id
                    for item in evidence
                    if isinstance(item, dict)
                    and item.get("use_type")
                    in {"lexical", "grammatical", "historical", "orthographic"}
                    and item.get("confidence") in {"medium", "high"}
                    for sense_id in item.get("supports_sense_ids", [])
                }
                declared = {
                    sense.get("id")
                    for sense in (senses if isinstance(senses, list) else [])
                    if isinstance(sense, dict) and isinstance(sense.get("id"), str)
                }
                if not declared <= supported:
                    errors.append(
                        f"{label}.source_evidence: every canonical sense needs medium/high supporting evidence"
                    )
        if (
            record_type == "construction"
            and isinstance(construction_spec, dict)
            and construction_spec.get("productivity") == "productive"
            and paradigm is None
        ):
            errors.append(
                f"{label}.paradigm: productive canonical construction requires a paradigm"
            )

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
    records: list[dict[str, Any]],
    *,
    source_registry_ids: set[str] | None = None,
    source_registry: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    if source_registry is not None:
        registry_ids = set(source_registry)
        source_registry_ids = (
            registry_ids
            if source_registry_ids is None
            else source_registry_ids & registry_ids
        )
    errors: list[str] = []
    ids: dict[str, str] = {}
    sense_ids: dict[str, str] = {}
    sense_owner: dict[str, str] = {}
    headwords: dict[str, list[dict[str, Any]]] = {}

    for index, record in enumerate(records):
        label = record.get("_source", f"record[{index}]")
        errors.extend(
            _validate_record(
                record,
                label,
                source_registry_ids,
                source_registry=source_registry,
            )
        )
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
                        record_id = record.get("id")
                        if isinstance(record_id, str):
                            sense_owner[sense_id] = record_id
        if record.get("record_type") in {"lexeme", "morpheme"}:
            forms = record.get("forms")
            conlang = forms.get("judeo_algonquin") if isinstance(forms, dict) else None
            headword = conlang.get("hebrew_script") if isinstance(conlang, dict) else None
            if isinstance(headword, str):
                normalized = normalize_search(headword)
                metadata = record.get("metadata")
                tags = metadata.get("tags", []) if isinstance(metadata, dict) else []
                prior_records = headwords.setdefault(normalized, [])
                if prior_records and "homonym" not in tags:
                    unmarked_group = [
                        prior
                        for prior in prior_records
                        if "homonym" not in prior.get("metadata", {}).get("tags", [])
                    ] + [record]
                    is_pinned_donor_overlay = False
                    if len(unmarked_group) == 2:
                        first, second = unmarked_group
                        first_layer = first.get("metadata", {}).get("lexical_layer")
                        second_layer = second.get("metadata", {}).get("lexical_layer")
                        first_id = first.get("id")
                        second_id = second.get("id")
                        first_dependencies = first.get("relations", {}).get(
                            "depends_on", []
                        )
                        second_dependencies = second.get("relations", {}).get(
                            "depends_on", []
                        )
                        is_pinned_donor_overlay = (
                            first_layer == "donor_candidate"
                            and second_layer == "direct_contact_inheritance"
                            and first_id in second_dependencies
                        ) or (
                            second_layer == "donor_candidate"
                            and first_layer == "direct_contact_inheritance"
                            and second_id in first_dependencies
                        )
                    if not is_pinned_donor_overlay:
                        errors.append(
                            f"{label}: duplicate normalized headword; mark an intentional homonym explicitly"
                        )
                prior_records.append(record)

    known_ids = set(ids)
    records_by_id = {
        record_id: record
        for record in records
        if isinstance((record_id := record.get("id")), str)
    }
    status_by_id = {
        record_id: record.get("status")
        for record in records
        if isinstance((record_id := record.get("id")), str)
    }
    revision_by_id = {
        record_id: record.get("revision") for record_id, record in records_by_id.items()
    }
    type_by_id = {
        record_id: record.get("record_type") for record_id, record in records_by_id.items()
    }
    for index, record in enumerate(records):
        label = record.get("_source", f"record[{index}]")
        relations = record.get("relations")
        if isinstance(relations, dict):
            for relation in RELATION_KEYS:
                related_ids = relations.get(relation)
                if not isinstance(related_ids, list):
                    continue
                for related_id in related_ids:
                    if isinstance(related_id, str) and related_id not in known_ids:
                        errors.append(f"{label}.relations.{relation}: unknown ID {related_id}")
            dependency_revisions = relations.get("dependency_revisions")
            if isinstance(dependency_revisions, dict):
                for dependency_id, expected_revision in dependency_revisions.items():
                    actual_revision = revision_by_id.get(dependency_id)
                    if actual_revision is not None and expected_revision != actual_revision:
                        errors.append(
                            f"{label}.relations.dependency_revisions.{dependency_id}: "
                            f"stale revision {expected_revision}; current revision is {actual_revision}"
                        )

        composition = record.get("composition")
        if isinstance(composition, dict):
            used_dependencies: set[str] = set()
            for component in composition.get("components", []):
                if not isinstance(component, dict):
                    continue
                dependency_id = component.get("record_id")
                dependency_revision = component.get("record_revision")
                sense_id = component.get("sense_id")
                if isinstance(dependency_id, str):
                    used_dependencies.add(dependency_id)
                    if dependency_id not in known_ids:
                        errors.append(
                            f"{label}.composition.components: unknown record ID {dependency_id}"
                        )
                    elif revision_by_id.get(dependency_id) != dependency_revision:
                        errors.append(
                            f"{label}.composition.components: stale revision for {dependency_id}"
                        )
                if isinstance(sense_id, str) and isinstance(dependency_id, str):
                    if sense_owner.get(sense_id) != dependency_id:
                        errors.append(
                            f"{label}.composition.components: sense {sense_id} does not belong to {dependency_id}"
                        )
            for construction_id in composition.get("construction_ids", []):
                if not isinstance(construction_id, str):
                    continue
                used_dependencies.add(construction_id)
                if construction_id not in known_ids:
                    errors.append(
                        f"{label}.composition.construction_ids: unknown ID {construction_id}"
                    )
                elif type_by_id.get(construction_id) != "construction":
                    errors.append(
                        f"{label}.composition.construction_ids: {construction_id} is not a construction"
                    )
            if isinstance(relations, dict) and used_dependencies != set(
                relations.get("depends_on", [])
            ):
                errors.append(
                    f"{label}.composition: used dependencies must exactly match relations.depends_on"
                )

        formation = record.get("formation")
        if isinstance(formation, dict):
            for formation_input in formation.get("inputs", []):
                if not isinstance(formation_input, dict):
                    continue
                if formation_input.get("input_type") == "language_record":
                    input_id = formation_input.get("input_id")
                    if isinstance(input_id, str):
                        if input_id not in known_ids:
                            errors.append(
                                f"{label}.formation.inputs: unknown language record ID {input_id}"
                            )
                        elif isinstance(relations, dict) and input_id not in relations.get(
                            "depends_on", []
                        ):
                            errors.append(
                                f"{label}.formation.inputs: language record {input_id} must be a dependency"
                            )
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
                    elif (
                        isinstance(construction_id, str)
                        and type_by_id.get(construction_id) != "construction"
                    ):
                        errors.append(
                            f"{label}.narrative_analysis: {construction_id} is not a construction"
                        )
        if record.get("status") == "canonical" and isinstance(relations, dict):
            for dependency in relations.get("depends_on", []):
                if status_by_id.get(dependency) not in {"reviewed", "canonical"}:
                    errors.append(
                        f"{label}.relations.depends_on: canonical record depends on unreviewed {dependency}"
                    )

    graph = {
        record_id: [
            dependency
            for dependency in (
                record.get("relations", {}).get("depends_on", [])
                if isinstance(record.get("relations"), dict)
                else []
            )
            if isinstance(dependency, str) and dependency in known_ids
        ]
        for record_id, record in records_by_id.items()
    }
    states: dict[str, int] = {}
    stack: list[str] = []

    def visit(record_id: str) -> None:
        state = states.get(record_id, 0)
        if state == 2:
            return
        if state == 1:
            start = stack.index(record_id) if record_id in stack else 0
            cycle = " -> ".join([*stack[start:], record_id])
            errors.append(f"dependency cycle: {cycle}")
            return
        states[record_id] = 1
        stack.append(record_id)
        for dependency in graph.get(record_id, []):
            visit(dependency)
        stack.pop()
        states[record_id] = 2

    for record_id in graph:
        visit(record_id)

    if errors:
        raise ValidationError(errors)
    for record in records:
        record.pop("_source", None)
    return records


def canonical_json(record: dict[str, Any]) -> str:
    clean = {key: value for key, value in record.items() if key != "_source"}
    return json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
