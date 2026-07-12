"""SQLite derived index with exact, full-text, and local vector search."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import struct
from pathlib import Path
from typing import Any, Iterable, Sequence

from .normalize import normalize_search, strip_hebrew_marks
from .records import canonical_json


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    record_type TEXT NOT NULL,
    revision INTEGER NOT NULL,
    status TEXT NOT NULL,
    level TEXT NOT NULL,
    hebrew TEXT NOT NULL,
    unpointed TEXT NOT NULL,
    romanization TEXT NOT NULL,
    english TEXT NOT NULL,
    notes TEXT NOT NULL,
    hebrew_norm TEXT NOT NULL,
    romanization_norm TEXT NOT NULL,
    english_norm TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    record_json TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
    id UNINDEXED,
    english,
    hebrew,
    unpointed,
    romanization,
    notes,
    tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TABLE IF NOT EXISTS record_aliases (
    record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    alias_kind TEXT NOT NULL,
    value TEXT NOT NULL,
    normalized TEXT NOT NULL,
    PRIMARY KEY (record_id, alias_kind, normalized)
);

CREATE TABLE IF NOT EXISTS embeddings (
    record_id TEXT NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    model TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    fingerprint TEXT NOT NULL,
    vector BLOB NOT NULL,
    PRIMARY KEY (record_id, model, dimensions)
);

CREATE INDEX IF NOT EXISTS records_status_idx ON records(status);
CREATE INDEX IF NOT EXISTS record_aliases_normalized_idx ON record_aliases(normalized);
CREATE INDEX IF NOT EXISTS embeddings_fingerprint_idx ON embeddings(fingerprint);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA_SQL)
    return connection


def _record_fields(record: dict[str, Any]) -> dict[str, str | int]:
    forms = record["forms"]
    conlang = forms["judeo_algonquin"]
    english = "\n".join(forms["english"])
    hebrew = conlang["hebrew_script"]
    unpointed = conlang.get("unpointed") or strip_hebrew_marks(hebrew)
    romanization = conlang["romanization"]
    note_values = [
        *record["notes"]["translation"],
        *record["notes"]["grammar"],
        *record["notes"]["design"],
        record["formation"]["formation_process"],
        record["formation"]["design_alignment"],
        *conlang.get("variants", []),
        *record["grammatical_features"],
        *(
            value
            for sense in record["senses"]
            for value in [
                *sense["glosses"],
                sense["definition"],
                sense["part_of_speech"],
                *sense["translations"]["literal"],
                *sense["translations"]["idiomatic"],
            ]
        ),
        *(
            value
            for evidence in record["source_evidence"]
            for value in [
                evidence["language"],
                evidence["lect"],
                evidence["source_form"],
                evidence["source_meaning"],
                evidence["grammatical_information"],
                evidence["locator"],
                evidence["uncertainty"],
            ]
            if value
        ),
        record["formation"]["formation_kind"],
        *(operation["description"] for operation in record["formation"]["operations"]),
        canonical_json(record["composition"]) if record["composition"] else "",
        canonical_json(record["construction_spec"]) if record["construction_spec"] else "",
        canonical_json(record["paradigm"]) if record["paradigm"] else "",
    ]
    notes = "\n".join(value for value in note_values if value)
    serialized = canonical_json(record)
    return {
        "id": record["id"],
        "record_type": record["record_type"],
        "revision": record["revision"],
        "status": record["status"],
        "level": record["level"],
        "hebrew": hebrew,
        "unpointed": unpointed,
        "romanization": romanization,
        "english": english,
        "notes": notes,
        "hebrew_norm": normalize_search(hebrew),
        "romanization_norm": normalize_search(romanization),
        "english_norm": normalize_search(english),
        "content_hash": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "record_json": serialized,
    }


def index_records(connection: sqlite3.Connection, records: Sequence[dict[str, Any]]) -> None:
    """Synchronize the derived index without discarding still-current vector rows."""

    fields = [_record_fields(record) for record in records]
    records_by_id = {record["id"]: record for record in records}
    ids = [str(field["id"]) for field in fields]
    with connection:
        for field in fields:
            connection.execute(
                """
                INSERT INTO records (
                    id, record_type, revision, status, level, hebrew, unpointed,
                    romanization, english, notes, hebrew_norm, romanization_norm,
                    english_norm, content_hash, record_json
                ) VALUES (
                    :id, :record_type, :revision, :status, :level, :hebrew, :unpointed,
                    :romanization, :english, :notes, :hebrew_norm, :romanization_norm,
                    :english_norm, :content_hash, :record_json
                )
                ON CONFLICT(id) DO UPDATE SET
                    record_type=excluded.record_type,
                    revision=excluded.revision,
                    status=excluded.status,
                    level=excluded.level,
                    hebrew=excluded.hebrew,
                    unpointed=excluded.unpointed,
                    romanization=excluded.romanization,
                    english=excluded.english,
                    notes=excluded.notes,
                    hebrew_norm=excluded.hebrew_norm,
                    romanization_norm=excluded.romanization_norm,
                    english_norm=excluded.english_norm,
                    content_hash=excluded.content_hash,
                    record_json=excluded.record_json
                """,
                field,
            )
            connection.execute("DELETE FROM records_fts WHERE id = ?", (field["id"],))
            connection.execute("DELETE FROM record_aliases WHERE record_id = ?", (field["id"],))
            record = records_by_id[field["id"]]
            conlang = record["forms"]["judeo_algonquin"]
            aliases = [
                *(("english", value) for value in record["forms"]["english"]),
                *(
                    ("sense_gloss", gloss)
                    for sense in record["senses"]
                    for gloss in sense["glosses"]
                ),
                ("hebrew", conlang["hebrew_script"]),
                ("unpointed", conlang.get("unpointed") or strip_hebrew_marks(conlang["hebrew_script"])),
                ("romanization", conlang["romanization"]),
                *(("variant", value) for value in conlang.get("variants", [])),
                *(
                    ("source_form", evidence["source_form"])
                    for evidence in record["source_evidence"]
                ),
            ]
            for alias_kind, value in aliases:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO record_aliases(record_id, alias_kind, value, normalized)
                    VALUES (?, ?, ?, ?)
                    """,
                    (field["id"], alias_kind, value, normalize_search(value)),
                )
            connection.execute(
                """
                INSERT INTO records_fts (id, english, hebrew, unpointed, romanization, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    field["id"],
                    field["english"],
                    field["hebrew"],
                    field["unpointed"],
                    field["romanization"],
                    field["notes"],
                ),
            )

        if ids:
            placeholders = ",".join("?" for _ in ids)
            stale_ids = [
                row[0]
                for row in connection.execute(
                    f"SELECT id FROM records WHERE id NOT IN ({placeholders})", ids
                )
            ]
        else:
            stale_ids = [row[0] for row in connection.execute("SELECT id FROM records")]
        for stale_id in stale_ids:
            connection.execute("DELETE FROM records_fts WHERE id = ?", (stale_id,))
            connection.execute("DELETE FROM records WHERE id = ?", (stale_id,))
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES ('record_count', ?)",
            (str(len(fields)),),
        )


def _status_clause(statuses: Sequence[str]) -> tuple[str, list[str]]:
    placeholders = ",".join("?" for _ in statuses)
    return f"r.status IN ({placeholders})", list(statuses)


def search_text(
    connection: sqlite3.Connection,
    query: str,
    *,
    statuses: Sequence[str] = ("candidate", "reviewed", "canonical"),
    limit: int = 10,
) -> list[dict[str, Any]]:
    if not query.strip() or limit < 1:
        return []
    normalized = normalize_search(query)
    status_sql, status_params = _status_clause(statuses)
    results: dict[str, dict[str, Any]] = {}

    alias_rows = connection.execute(
        f"""
        SELECT r.*,
            CASE
              WHEN a.alias_kind = 'source_form' THEN 95.0
              ELSE 100.0
            END AS rank_score
        FROM record_aliases a JOIN records r ON r.id=a.record_id
        WHERE a.normalized=? AND {status_sql}
        ORDER BY rank_score DESC, r.id
        LIMIT ?
        """,
        [normalized, *status_params, limit],
    )
    for row in alias_rows:
        score = float(row["rank_score"])
        if row["id"] not in results or score > results[row["id"]]["score"]:
            results[row["id"]] = _result(row, lexical_score=score)

    exact_rows = connection.execute(
        f"""
        SELECT r.*,
            CASE
              WHEN r.hebrew_norm = ? OR r.romanization_norm = ? OR r.english_norm = ? THEN 100.0
              WHEN instr(r.hebrew_norm, ?) > 0 OR instr(r.romanization_norm, ?) > 0
                   OR instr(r.english_norm, ?) > 0 THEN 90.0
              ELSE 0.0
            END AS rank_score
        FROM records r
        WHERE {status_sql}
          AND (r.hebrew_norm = ? OR r.romanization_norm = ? OR r.english_norm = ?
               OR instr(r.hebrew_norm, ?) > 0 OR instr(r.romanization_norm, ?) > 0
               OR instr(r.english_norm, ?) > 0)
        ORDER BY rank_score DESC, r.id
        LIMIT ?
        """,
        [
            normalized,
            normalized,
            normalized,
            normalized,
            normalized,
            normalized,
            *status_params,
            normalized,
            normalized,
            normalized,
            normalized,
            normalized,
            normalized,
            limit,
        ],
    )
    for row in exact_rows:
        score = float(row["rank_score"])
        if row["id"] not in results or score > results[row["id"]]["score"]:
            results[row["id"]] = _result(row, lexical_score=score)

    if len(results) < limit:
        fts_query = '"' + normalized.replace('"', '""') + '"'
        try:
            fts_rows = connection.execute(
                f"""
                SELECT r.*, bm25(records_fts) AS fts_rank
                FROM records_fts
                JOIN records r ON r.id = records_fts.id
                WHERE records_fts MATCH ? AND {status_sql}
                ORDER BY fts_rank, r.id
                LIMIT ?
                """,
                [fts_query, *status_params, limit],
            )
            for row in fts_rows:
                if row["id"] not in results:
                    score = max(1.0, 80.0 - abs(float(row["fts_rank"])))
                    results[row["id"]] = _result(row, lexical_score=score)
        except sqlite3.OperationalError:
            pass

    return sorted(results.values(), key=lambda item: (-item["score"], item["id"]))[:limit]


def _result(
    row: sqlite3.Row,
    *,
    lexical_score: float = 0.0,
    semantic_score: float | None = None,
) -> dict[str, Any]:
    record = json.loads(row["record_json"])
    return {
        "id": row["id"],
        "record_type": row["record_type"],
        "status": row["status"],
        "level": row["level"],
        "english": record["forms"]["english"],
        "hebrew_script": row["hebrew"],
        "romanization": row["romanization"],
        "score": lexical_score if semantic_score is None else semantic_score,
        "lexical_score": lexical_score,
        "semantic_score": semantic_score,
    }


def pack_vector(vector: Sequence[float]) -> bytes:
    if not vector:
        raise ValueError("embedding vector cannot be empty")
    if any(not math.isfinite(value) for value in vector):
        raise ValueError("embedding vector contains a non-finite value")
    return struct.pack(f"<{len(vector)}f", *vector)


def unpack_vector(blob: bytes, dimensions: int) -> tuple[float, ...]:
    if len(blob) != dimensions * 4:
        raise ValueError("stored vector byte length does not match dimensions")
    return struct.unpack(f"<{dimensions}f", blob)


def put_embedding(
    connection: sqlite3.Connection,
    record_id: str,
    model: str,
    dimensions: int,
    fingerprint: str,
    vector: Sequence[float],
) -> None:
    if len(vector) != dimensions:
        raise ValueError(f"expected {dimensions} dimensions, received {len(vector)}")
    with connection:
        connection.execute(
            """
            INSERT INTO embeddings(record_id, model, dimensions, fingerprint, vector)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(record_id, model, dimensions) DO UPDATE SET
                fingerprint=excluded.fingerprint,
                vector=excluded.vector
            """,
            (record_id, model, dimensions, fingerprint, pack_vector(vector)),
        )


def embedding_fingerprint(
    connection: sqlite3.Connection, record_id: str, model: str, dimensions: int
) -> str | None:
    row = connection.execute(
        "SELECT fingerprint FROM embeddings WHERE record_id=? AND model=? AND dimensions=?",
        (record_id, model, dimensions),
    ).fetchone()
    return None if row is None else str(row[0])


def _dependencies_current(connection: sqlite3.Connection, record: dict[str, Any]) -> bool:
    relations = record.get("relations")
    if not isinstance(relations, dict):
        return False
    expected = relations.get("dependency_revisions")
    if not isinstance(expected, dict):
        return False
    for dependency_id, dependency_revision in expected.items():
        row = connection.execute(
            "SELECT revision FROM records WHERE id=?", (dependency_id,)
        ).fetchone()
        if row is None or row["revision"] != dependency_revision:
            return False
    return True


def count_fresh_embeddings(
    connection: sqlite3.Connection,
    *,
    model: str,
    dimensions: int,
    statuses: Sequence[str] = ("candidate", "reviewed", "canonical"),
) -> int:
    """Count usable vectors, excluding cached embeddings for changed records."""

    status_sql, params = _status_clause(statuses)
    rows = connection.execute(
        f"""
        SELECT r.record_json, e.fingerprint AS embedding_fingerprint
        FROM embeddings e JOIN records r ON r.id=e.record_id
        WHERE e.model=? AND e.dimensions=? AND {status_sql}
        """,
        [model, dimensions, *params],
    )
    # Local import avoids the embeddings -> store dependency cycle.
    from .embeddings import record_fingerprint

    count = 0
    for row in rows:
        record = json.loads(row["record_json"])
        if not _dependencies_current(connection, record):
            continue
        if row["embedding_fingerprint"] == record_fingerprint(record, model, dimensions):
            count += 1
    return count


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("vectors must have the same non-zero length")
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def search_vectors(
    connection: sqlite3.Connection,
    query_vector: Sequence[float],
    *,
    model: str,
    dimensions: int,
    statuses: Sequence[str] = ("candidate", "reviewed", "canonical"),
    limit: int = 10,
) -> list[dict[str, Any]]:
    if len(query_vector) != dimensions:
        raise ValueError("query vector dimensions do not match index")
    status_sql, params = _status_clause(statuses)
    rows = connection.execute(
        f"""
        SELECT r.*, e.vector, e.fingerprint AS embedding_fingerprint
        FROM embeddings e JOIN records r ON r.id=e.record_id
        WHERE e.model=? AND e.dimensions=? AND {status_sql}
        """,
        [model, dimensions, *params],
    )
    scored: list[dict[str, Any]] = []
    for row in rows:
        # Keep stale vectors cached for audit/reuse decisions, but never return them.
        # The import is local to avoid the embeddings -> store module dependency cycle.
        from .embeddings import record_fingerprint

        record = json.loads(row["record_json"])
        if not _dependencies_current(connection, record):
            continue
        expected = record_fingerprint(record, model, dimensions)
        if row["embedding_fingerprint"] != expected:
            continue
        stored = unpack_vector(row["vector"], dimensions)
        semantic_score = cosine_similarity(query_vector, stored)
        scored.append(_result(row, semantic_score=semantic_score))
    return sorted(scored, key=lambda item: (-item["score"], item["id"]))[:limit]


def merge_hybrid_results(
    lexical: Iterable[dict[str, Any]],
    semantic: Iterable[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Keep exact/FTS evidence dominant and use semantics for recall."""

    merged: dict[str, dict[str, Any]] = {item["id"]: dict(item) for item in semantic}
    for item in lexical:
        existing = merged.get(item["id"])
        if existing:
            item = dict(item)
            item["semantic_score"] = existing.get("semantic_score")
        merged[item["id"]] = dict(item)
    return sorted(
        merged.values(),
        key=lambda item: (
            -float(item.get("lexical_score") or 0.0),
            -float(item.get("semantic_score") or -1.0),
            item["id"],
        ),
    )[:limit]
