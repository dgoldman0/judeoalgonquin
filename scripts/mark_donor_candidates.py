"""Mark source-facing lexical records as donor ingredients, not language canon."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
DEFAULT_PATHS = [
    ROOT / "data" / "entries" / "n1-pilot.jsonl",
    ROOT / "data" / "entries" / "n1-core-lexicon.jsonl",
]
UPDATED_AT = "2026-07-13T00:50:00Z"
DONOR_CHANGE_NOTE = (
    "Classified the source-facing lexical record as a donor candidate so evidence "
    "cannot be mistaken for a finished contact-language word."
)
DEPENDENCY_CHANGE_NOTE = (
    "Refreshed dependency revisions after the source-facing lexical layer was "
    "classified as donor evidence."
)


def mark(path: Path) -> tuple[list[dict], int]:
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    changed = 0
    changed_donor_ids: set[str] = set()
    for record in records:
        if record["record_type"] not in {"lexeme", "morpheme"}:
            continue
        source_ids = {
            evidence["source_id"] for evidence in record.get("source_evidence", [])
        }
        if not source_ids:
            continue
        metadata = record["metadata"]
        prior = metadata.get("lexical_layer")
        if prior not in {None, "donor_candidate"}:
            raise ValueError(
                f"{record['id']}: refusing to replace lexical layer {prior!r}"
            )
        if prior is None:
            metadata["lexical_layer"] = "donor_candidate"
        if record.get("change_note") != DONOR_CHANGE_NOTE:
            record["revision"] += 1
            record["updated_at"] = UPDATED_AT
            record["change_note"] = DONOR_CHANGE_NOTE
            changed_donor_ids.add(record["id"])
            changed += 1

    if changed_donor_ids:
        by_id = {record["id"]: record for record in records}
        affected: set[str] = set()
        frontier = set(changed_donor_ids)
        while frontier:
            next_frontier = {
                record["id"]
                for record in records
                if record["id"] not in changed_donor_ids | affected
                and frontier & set(record["relations"]["depends_on"])
            }
            affected.update(next_frontier)
            frontier = next_frontier

        while affected:
            ready = [
                record
                for record in records
                if record["id"] in affected
                and not (set(record["relations"]["depends_on"]) & affected)
            ]
            if not ready:
                raise ValueError(f"{path}: dependency cycle while refreshing revisions")
            for record in ready:
                dependencies = record["relations"]["depends_on"]
                record["relations"]["dependency_revisions"] = {
                    dependency: by_id[dependency]["revision"] for dependency in dependencies
                }
                composition = record.get("composition")
                if isinstance(composition, dict):
                    for component in composition["components"]:
                        dependency = component["record_id"]
                        component["record_revision"] = by_id[dependency]["revision"]
                record["revision"] += 1
                record["updated_at"] = UPDATED_AT
                record["change_note"] = DEPENDENCY_CHANGE_NOTE
                affected.remove(record["id"])
                changed += 1
    return records, changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, default=DEFAULT_PATHS)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    total = 0
    for path in args.paths:
        records, changed = mark(path)
        total += changed
        if changed and not args.check:
            path.write_text(
                "".join(
                    json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
                    for record in records
                ),
                encoding="utf-8",
            )
        print(json.dumps({"path": str(path), "changed": changed}))
    return 1 if args.check and total else 0


if __name__ == "__main__":
    raise SystemExit(main())
