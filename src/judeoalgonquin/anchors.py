"""Loading and cross-reference validation for creative-anchor ledgers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .records import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANCHOR_SOURCE_ROOT = PROJECT_ROOT / "references" / "creative-anchors"
ANCHOR_SCHEMA_PATH = PROJECT_ROOT / "schema" / "creative-anchor.schema.json"

SOURCE_SECTION_LABELS = {
    "Verse 1",
    "Verse 2",
    "Verse 3",
    "Verse 4",
    "Chorus",
    "Bridge",
    "Final Chorus",
}


CONTACT_LAYERS = {
    "direct_contact_inheritance",
    "contact_native_formation",
    "learned_literary_reborrowing",
}

CONTACT_RECORD_TAGS = {
    "contact-clause",
    "contact-grammar",
    "contact-phrase",
    "contact-paragraph",
}


def _is_contact_record(record: dict[str, Any]) -> bool:
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        return False
    if metadata.get("lexical_layer") in CONTACT_LAYERS:
        return True
    tags = metadata.get("tags", [])
    return isinstance(tags, list) and bool(CONTACT_RECORD_TAGS.intersection(tags))


def _source_path(ledger: dict[str, Any]) -> Path:
    declared = Path(str(ledger.get("source_file", "")))
    if declared.is_absolute() or ".." in declared.parts:
        raise ValueError("source_file must be a repository-relative path without '..'")
    if declared.parts[:2] != ("references", "creative-anchors"):
        raise ValueError("source_file must remain under references/creative-anchors")
    candidate = (PROJECT_ROOT / declared).resolve()
    if not candidate.is_relative_to(ANCHOR_SOURCE_ROOT.resolve()):
        raise ValueError("source_file escapes the protected creative-anchor tree")
    return candidate


def _extract_source_block(path: Path, heading: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    try:
        start = next(index for index, line in enumerate(lines) if line.rstrip("\r\n") == heading)
    except StopIteration as exc:
        raise ValueError(f"heading not found: {heading}") from exc
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return "".join(lines[start:end])


def _source_pairs(block: str) -> list[tuple[str, str]]:
    """Extract the exact ordered Hebrew/English line pairs from either anchor format."""

    lines = block.splitlines()
    divider = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip() in {"================", "===Qausi Translation==="}
        ),
        None,
    )
    if divider is None:
        raise ValueError("protected source block lacks its Hebrew/English divider")

    def content(source_lines: list[str]) -> list[str]:
        values: list[str] = []
        for raw in source_lines:
            line = raw.strip()
            if (
                not line
                or line.startswith("## ")
                or line in SOURCE_SECTION_LABELS
                or line in {"English quasitranslation", "---"}
            ):
                continue
            values.append(line)
        return values

    hebrew = content(lines[:divider])
    english = content(lines[divider + 1 :])
    if len(hebrew) != len(english):
        raise ValueError(
            f"protected source has {len(hebrew)} Hebrew lines but {len(english)} English lines"
        )
    return list(zip(hebrew, english))


def _schema_errors(ledger: dict[str, Any], source: str) -> list[str]:
    schema = json.loads(ANCHOR_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    public = {key: value for key, value in ledger.items() if key != "_source"}
    errors: list[str] = []
    for error in sorted(
        validator.iter_errors(public),
        key=lambda item: tuple(str(part) for part in item.path),
    ):
        suffix = "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.path
        )
        errors.append(f"{source}{suffix}: schema: {error.message}")
    return errors


def discover_anchor_ledgers(path: str | Path) -> list[Path]:
    root = Path(path)
    if root.is_file():
        return [root]
    if not root.exists():
        raise FileNotFoundError(root)
    return sorted(candidate for candidate in root.rglob("*.json") if candidate.is_file())


def load_anchor_ledgers(path: str | Path) -> list[dict[str, Any]]:
    ledgers: list[dict[str, Any]] = []
    errors: list[str] = []
    for source in discover_anchor_ledgers(path):
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{source}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{source}: ledger must be a JSON object")
            continue
        value["_source"] = str(source)
        ledgers.append(value)
    if errors:
        raise ValidationError(errors)
    return ledgers


def _record_links(ledger: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    links: list[tuple[str, dict[str, Any]]] = []
    for index, legacy in enumerate(ledger.get("legacy_form_inventory", [])):
        if isinstance(legacy, dict):
            for link in legacy.get("current_record_links", []):
                if isinstance(link, dict):
                    links.append((f"legacy_form_inventory[{index}]", link))
    for index, segment in enumerate(ledger.get("segments", [])):
        if isinstance(segment, dict):
            for link in segment.get("current_record_links", []):
                if isinstance(link, dict):
                    links.append((f"segments[{index}]", link))
    for index, requirement in enumerate(ledger.get("requirements", [])):
        if isinstance(requirement, dict):
            for link in requirement.get("current_record_links", []):
                if isinstance(link, dict):
                    links.append((f"requirements[{index}]", link))
    return links


def _validate_link_uniqueness(
    items: Any, family: str, source: str, errors: list[str]
) -> None:
    if not isinstance(items, list):
        return
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        seen: set[tuple[Any, Any, Any]] = set()
        for link in item.get("current_record_links", []):
            if not isinstance(link, dict):
                continue
            key = (link.get("record_id"), link.get("sense_id"), link.get("relationship"))
            if key in seen:
                errors.append(
                    f"{source}.{family}[{index}].current_record_links: duplicate link {key!r}"
                )
            seen.add(key)


def validate_anchor_ledgers(
    ledgers: list[dict[str, Any]], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Validate stable IDs, revision pins, and the anchor-to-record evidence boundary.

    The public JSON Schema is enforced here alongside relationships that require
    the complete set of ledgers, protected source texts, and language records.
    """

    errors: list[str] = []
    records_by_id = {
        record["id"]: record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    seen_anchors: set[str] = set()
    seen_segments: set[str] = set()

    for ledger_index, ledger in enumerate(ledgers):
        source = ledger.get("_source", f"anchor[{ledger_index}]")
        errors.extend(_schema_errors(ledger, str(source)))
        anchor_id = ledger.get("anchor_id")
        if not isinstance(anchor_id, str):
            errors.append(f"{source}.anchor_id: string required")
            continue
        if anchor_id in seen_anchors:
            errors.append(f"{source}.anchor_id: duplicate {anchor_id}")
        seen_anchors.add(anchor_id)

        segments = ledger.get("segments")
        if not isinstance(segments, list) or not segments:
            errors.append(f"{source}.segments: non-empty array required")
            continue
        local_segments: dict[str, int] = {}
        orders: list[int] = []
        for index, segment in enumerate(segments):
            label = f"{source}.segments[{index}]"
            if not isinstance(segment, dict):
                errors.append(f"{label}: object required")
                continue
            segment_id = segment.get("segment_id")
            order = segment.get("order")
            if not isinstance(segment_id, str):
                errors.append(f"{label}.segment_id: string required")
                continue
            if segment_id in seen_segments:
                errors.append(f"{label}.segment_id: duplicate {segment_id}")
            seen_segments.add(segment_id)
            local_segments[segment_id] = index
            if isinstance(order, int) and not isinstance(order, bool):
                orders.append(order)
            else:
                errors.append(f"{label}.order: integer required")
            repeat_of = segment.get("repeat_of")
            if repeat_of is not None:
                prior_index = local_segments.get(repeat_of)
                if prior_index is None or prior_index >= index:
                    errors.append(f"{label}.repeat_of: must name an earlier local segment")
                else:
                    target = segments[prior_index]
                    if isinstance(target, dict) and (
                        segment.get("extant_hebrew") != target.get("extant_hebrew")
                        or segment.get("english_quasitranslation")
                        != target.get("english_quasitranslation")
                    ):
                        errors.append(
                            f"{label}.repeat_of: repeated source text must exactly match "
                            f"{repeat_of}"
                        )
        if sorted(orders) != list(range(1, len(segments) + 1)):
            errors.append(f"{source}.segments: order values must be contiguous from 1")

        local_ids = set(local_segments)
        source_block = ledger.get("source_block")
        if isinstance(source_block, dict):
            try:
                source_path = _source_path(ledger)
            except ValueError as exc:
                errors.append(f"{source}.source_file: {exc}")
                source_path = None
            if source_path is not None and not source_path.exists():
                errors.append(f"{source}.source_file: not found: {source_path}")
            elif source_path is not None:
                try:
                    block = _extract_source_block(
                        source_path, str(source_block.get("start_heading", ""))
                    )
                except ValueError as exc:
                    errors.append(f"{source}.source_block: {exc}")
                else:
                    digest = hashlib.sha256(block.encode("utf-8")).hexdigest()
                    if source_block.get("sha256") != digest:
                        errors.append(
                            f"{source}.source_block.sha256: expected current block {digest}"
                        )
                    try:
                        source_pairs = _source_pairs(block)
                    except ValueError as exc:
                        errors.append(f"{source}.source_block: {exc}")
                        source_pairs = []
                    if source_block.get("paired_line_count") != len(source_pairs):
                        errors.append(
                            f"{source}.source_block.paired_line_count: protected source has "
                            f"{len(source_pairs)} pairs"
                        )
                    if len(segments) != len(source_pairs):
                        errors.append(
                            f"{source}.segments: ledger has {len(segments)} segments but "
                            f"protected source has {len(source_pairs)} pairs"
                        )
                    for index, (hebrew, english) in enumerate(source_pairs):
                        if index >= len(segments) or not isinstance(segments[index], dict):
                            break
                        segment = segments[index]
                        if segment.get("extant_hebrew") != hebrew:
                            errors.append(
                                f"{source}.segments[{index}].extant_hebrew: does not match "
                                "the ordered protected source line"
                            )
                        if segment.get("english_quasitranslation") != english:
                            errors.append(
                                f"{source}.segments[{index}].english_quasitranslation: "
                                "does not match the paired protected source line"
                            )

        functions = {
            item.get("function_id")
            for item in ledger.get("protected_functions", [])
            if isinstance(item, dict) and isinstance(item.get("function_id"), str)
        }
        if len(functions) != len(ledger.get("protected_functions", [])):
            errors.append(f"{source}.protected_functions: IDs must be present and unique")
        used_functions: set[str] = set()
        for index, segment in enumerate(segments):
            if not isinstance(segment, dict):
                continue
            dispositions = segment.get("function_dispositions", [])
            disposition_ids = [
                item.get("function_id")
                for item in dispositions
                if isinstance(item, dict)
            ]
            if len(set(disposition_ids)) != len(disposition_ids):
                errors.append(
                    f"{source}.segments[{index}].function_dispositions: duplicate function"
                )
            for disposition in dispositions:
                if not isinstance(disposition, dict):
                    continue
                function_id = disposition.get("function_id")
                if function_id not in functions:
                    errors.append(
                        f"{source}.segments[{index}].function_dispositions: "
                        f"unknown {function_id}"
                    )
                elif isinstance(function_id, str):
                    used_functions.add(function_id)
                if (
                    disposition.get("disposition") == "depart"
                    and not isinstance(disposition.get("human_review"), dict)
                ):
                    errors.append(
                        f"{source}.segments[{index}].function_dispositions: "
                        "depart requires human review"
                    )
        unused_functions = sorted(functions - used_functions)
        if unused_functions:
            errors.append(
                f"{source}.protected_functions: unused IDs: {', '.join(unused_functions)}"
            )

        for family in ("legacy_form_inventory", "segments", "requirements"):
            _validate_link_uniqueness(ledger.get(family), family, str(source), errors)

        for family in ("legacy_form_inventory", "requirements"):
            for index, item in enumerate(ledger.get(family, [])):
                if not isinstance(item, dict):
                    continue
                for segment_id in item.get("segment_ids", []):
                    if segment_id not in local_ids:
                        errors.append(
                            f"{source}.{family}[{index}].segment_ids: unknown {segment_id}"
                        )

        requirements = {
            item.get("requirement_id")
            for item in ledger.get("requirements", [])
            if isinstance(item, dict) and isinstance(item.get("requirement_id"), str)
        }
        if len(requirements) != len(ledger.get("requirements", [])):
            errors.append(f"{source}.requirements: IDs must be present and unique")
        for index, requirement in enumerate(ledger.get("requirements", [])):
            if not isinstance(requirement, dict):
                continue
            links = [
                link
                for link in requirement.get("current_record_links", [])
                if isinstance(link, dict)
            ]
            has_contact = any(link.get("relationship") == "contact_candidate" for link in links)
            has_donor = any(link.get("relationship") == "donor_lead" for link in links)
            has_lead = has_contact or has_donor or any(
                link.get("relationship") == "conflict_probe" for link in links
            )
            status = requirement.get("status")
            label = f"{source}.requirements[{index}].status"
            if status == "gap" and (has_contact or has_donor):
                errors.append(f"{label}: gap cannot contain contact or donor coverage")
            elif status == "donor_lead" and (not has_donor or has_contact):
                errors.append(f"{label}: donor_lead requires donor links and no contact link")
            elif status == "contact_candidate" and not has_contact:
                errors.append(f"{label}: contact_candidate requires a contact-language link")
            elif status == "partial" and not has_lead:
                errors.append(f"{label}: partial requires at least one explicit lead or conflict")
        for index, test in enumerate(ledger.get("acceptance_tests", [])):
            if not isinstance(test, dict):
                continue
            for requirement_id in test.get("requirement_ids", []):
                if requirement_id not in requirements:
                    errors.append(
                        f"{source}.acceptance_tests[{index}].requirement_ids: "
                        f"unknown {requirement_id}"
                    )
            status = test.get("status")
            blocker = test.get("blocker")
            evidence = test.get("evidence")
            label = f"{source}.acceptance_tests[{index}]"
            if status == "blocked" and (
                not isinstance(blocker, str) or not blocker.strip()
            ):
                errors.append(f"{label}.blocker: blocked tests require a nonempty blocker")
            if status == "passing" and blocker is not None:
                errors.append(f"{label}.blocker: passing tests require null")
            if status == "passing" and not isinstance(evidence, dict):
                errors.append(
                    f"{label}.evidence: passing requires human-review or evaluation evidence"
                )
            if status != "passing" and evidence is not None:
                errors.append(f"{label}.evidence: only passing tests may carry evidence")

        for location, link in _record_links(ledger):
            record_id = link.get("record_id")
            record = records_by_id.get(record_id)
            label = f"{source}.{location}.current_record_links"
            if record is None:
                errors.append(f"{label}: unknown language record {record_id}")
                continue
            if link.get("record_revision") != record.get("revision"):
                errors.append(
                    f"{label}: stale revision for {record_id}; "
                    f"expected {record.get('revision')}"
                )
            sense_id = link.get("sense_id")
            record_sense_ids = {
                sense.get("id")
                for sense in record.get("senses", [])
                if isinstance(sense, dict)
            }
            if sense_id not in record_sense_ids:
                errors.append(f"{label}: {sense_id} is not owned by {record_id}")
            relationship = link.get("relationship")
            layer = record.get("metadata", {}).get("lexical_layer")
            if relationship == "donor_lead" and layer != "donor_candidate":
                errors.append(f"{label}: {record_id} is not a donor candidate")
            if relationship == "contact_candidate" and not _is_contact_record(record):
                errors.append(f"{label}: {record_id} is not a contact-language candidate")
            expected_coverage = None
            if relationship == "donor_lead":
                expected_coverage = "donor_only"
            elif relationship == "conflict_probe":
                expected_coverage = "conflict"
            elif relationship == "contact_candidate":
                expected_coverage = {
                    "draft": "contact_candidate",
                    "candidate": "contact_candidate",
                    "reviewed": "contact_reviewed",
                    "canonical": "contact_canonical",
                }.get(record.get("status"))
            if expected_coverage is None or link.get("coverage") != expected_coverage:
                errors.append(
                    f"{label}: coverage for {record_id} must be {expected_coverage}"
                )

        honesty = ledger.get("source_honesty")
        if not isinstance(honesty, dict) or honesty.get("claim_status") != (
            "creative_input_not_source_attestation"
        ):
            errors.append(f"{source}.source_honesty: creative-input boundary required")

    if not ledgers:
        errors.append("creative anchors: at least one ledger required")
    if errors:
        raise ValidationError(errors)
    return ledgers
