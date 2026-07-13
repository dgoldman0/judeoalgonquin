"""Command-line entry point. All paid actions are explicit and capped."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .anchors import load_anchor_ledgers, validate_anchor_ledgers
from .budget import (
    budget_snapshot,
    complete_paid_embedding_run,
    fail_paid_embedding_run,
    load_policy,
    reserve_paid_embedding_run,
    reserve_paid_embedding_checkpoint,
    token_upper_bound,
)
from .evaluate import (
    evaluate_anchor_chorus_compositions,
    evaluate_motion_action_compositions,
    evaluate_perception_compositions,
    evaluate_pilot_compositions,
    evaluate_static_place_compositions,
    evaluate_semantic_rankings,
    load_semantic_queries,
    load_typed_semantic_queries,
)
from .embeddings import (
    DEFAULT_DIMENSIONS,
    DEFAULT_MODEL,
    MAX_LIVE_INPUTS,
    OpenAIEmbedder,
    embedding_text,
    record_fingerprint,
    records_needing_embeddings,
)
from .records import (
    ValidationError,
    load_records,
    load_source_registry,
    validate_records,
)
from .store import (
    connect,
    count_fresh_embeddings,
    index_records,
    merge_hybrid_results,
    put_embedding,
    put_embeddings_atomic,
    search_text,
    search_vectors,
)


DEFAULT_DATA = "data/entries"
DEFAULT_ANCHORS = "data/creative-anchors"
DEFAULT_DB = ".local/judeoalgonquin.sqlite3"
DEFAULT_FIXTURE = "tests/fixtures/creative_anchor_candidates.jsonl"
DEFAULT_SMOKE_DB = ".local/embedding-smoke.sqlite3"
DEFAULT_SMOKE_MANIFEST = ".local/embedding-smoke-manifest.json"
SMOKE_REPORT = "docs/reports/embedding-smoke-2026-07-12.json"
DEFAULT_PILOT_DATA = "data/entries/n1-pilot.jsonl"
DEFAULT_PILOT_QUERIES = "tests/fixtures/n1_pilot_semantic_queries.json"
DEFAULT_PILOT_DB = ".local/n1-pilot.sqlite3"
PILOT_EMBEDDING_REPORT = "docs/reports/n1-pilot-embedding-evaluation-2026-07-12.json"
PILOT_LIVE_INPUTS = 25
DEFAULT_N1_CORE_DATA = "data/entries"
DEFAULT_N1_CORE_QUERIES = "tests/fixtures/n1_core_semantic_queries.json"
DEFAULT_N1_CORE_DB = ".local/n1-core.sqlite3"
N1_CORE_EMBEDDING_REPORT = "docs/reports/n1-core-embedding-evaluation-2026-07-12.json"
N1_CORE_RECORDS = 92
N1_CORE_QUERIES = 12
N1_CORE_LIVE_INPUTS = N1_CORE_RECORDS + N1_CORE_QUERIES
# Keep a conservative byte-level planning guard while allowing a complete
# twelve-cell construction to remain one retrievable record. Provider limits
# remain independent of this stricter project planning guard.
N1_CORE_MAX_INPUT_BYTES = 16384
DEFAULT_STATIC_PLACE_QUERIES = "tests/fixtures/static_place_semantic_queries.json"
DEFAULT_STATIC_PLACE_DB = ".local/static-place-semantic-bootstrap.sqlite3"
STATIC_PLACE_EMBEDDING_REPORT = (
    "docs/reports/static-place-semantic-bootstrap-2026-07-13.json"
)
STATIC_PLACE_RECORDS = 180
STATIC_PLACE_QUERIES = 16
STATIC_PLACE_EXPECTED_DATA_SHA256 = (
    "2af1fd2ad2976aea64b9e7a1281b04a3a3fefd5f56b6d07f5ccaa6a7b3c37f60"
)
STATIC_PLACE_EXPECTED_QUERY_SHA256 = (
    "6c3931808546a0e7d5f7939b8a09ff41ad36bd46b2ecdafded9dfe79c2f4e181"
)
STATIC_PLACE_RUN_KIND = "static-place-embedding-checkpoint"
SOURCE_REGISTRY = "references/sources.yaml"
SMOKE_QUERY = "home, dwelling, and the place where people live together"


def _records(path: str) -> list[dict[str, Any]]:
    source_registry = load_source_registry(SOURCE_REGISTRY)
    return validate_records(load_records(path), source_registry=source_registry)


def _statuses(value: str) -> tuple[str, ...]:
    statuses = tuple(part.strip() for part in value.split(",") if part.strip())
    allowed = {"candidate", "reviewed", "canonical", "deprecated", "rejected"}
    if not statuses or not set(statuses) <= allowed:
        raise argparse.ArgumentTypeError("invalid comma-separated status list")
    return statuses


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _write_json_atomic(path: str | Path, value: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def _chunk_embedding_inputs(
    texts: Sequence[str],
    *,
    max_inputs: int,
    max_utf8_bytes: int,
    max_input_utf8_bytes: int,
) -> list[list[str]]:
    """Create deterministic order-preserving batches under all local caps."""

    if not texts:
        raise ValueError("embedding checkpoint requires at least one input")
    chunks: list[list[str]] = []
    current: list[str] = []
    current_bytes = 0
    for text_value in texts:
        if not isinstance(text_value, str) or not text_value.strip():
            raise ValueError("embedding checkpoint inputs must be non-empty strings")
        size = len(text_value.encode("utf-8"))
        if size > max_input_utf8_bytes:
            raise ValueError("an embedding input exceeds the conservative per-input cap")
        if current and (
            len(current) >= max_inputs or current_bytes + size > max_utf8_bytes
        ):
            chunks.append(current)
            current = []
            current_bytes = 0
        current.append(text_value)
        current_bytes += size
    if current:
        chunks.append(current)
    return chunks


def command_validate(args: argparse.Namespace) -> int:
    records = _records(args.data)
    _print_json({"valid": True, "records": len(records), "data": args.data})
    return 0


def command_validate_anchors(args: argparse.Namespace) -> int:
    records = _records(args.data)
    anchors = validate_anchor_ledgers(load_anchor_ledgers(args.anchors), records)
    segment_count = sum(len(anchor["segments"]) for anchor in anchors)
    requirement_count = sum(len(anchor["requirements"]) for anchor in anchors)
    _print_json(
        {
            "valid": True,
            "anchors": len(anchors),
            "segments": segment_count,
            "requirements": requirement_count,
            "anchor_data": args.anchors,
            "language_data": args.data,
        }
    )
    return 0


def command_build(args: argparse.Namespace) -> int:
    records = _records(args.data)
    connection = connect(args.db)
    try:
        index_records(connection, records)
    finally:
        connection.close()
    _print_json({"indexed": len(records), "database": args.db})
    return 0


def command_evaluate(args: argparse.Namespace) -> int:
    records = _records(args.data)
    findings = [
        *evaluate_pilot_compositions(records),
        *evaluate_anchor_chorus_compositions(records),
        *evaluate_perception_compositions(records),
        *evaluate_static_place_compositions(records),
        *evaluate_motion_action_compositions(records),
    ]
    _print_json(
        {
            "valid": not findings,
            "records": len(records),
            "data": args.data,
            "construction_findings": findings,
        }
    )
    return 0 if not findings else 1


def command_search(args: argparse.Namespace) -> int:
    connection = connect(args.db)
    try:
        lexical = search_text(
            connection, args.query, statuses=args.statuses, limit=args.limit
        )
        if not args.semantic:
            _print_json({"query": args.query, "mode": "lexical", "results": lexical})
            return 0
        if not args.live:
            raise ValueError("semantic search is a paid API action; repeat with --live")
        vector_count = count_fresh_embeddings(
            connection,
            model=args.model,
            dimensions=args.dimensions,
            statuses=args.statuses,
        )
        if vector_count == 0:
            raise ValueError(
                "no fresh matching stored embeddings; run the capped embed command first"
            )
        texts = [args.query]
        reservation = reserve_paid_embedding_run(
            "semantic-search", texts, model=args.model, dimensions=args.dimensions
        )
        try:
            embedder = OpenAIEmbedder(model=args.model, dimensions=args.dimensions)
            batch = embedder.embed(texts)
            complete_paid_embedding_run(reservation, batch.prompt_tokens)
        except Exception as exc:
            fail_paid_embedding_run(reservation, type(exc).__name__)
            raise
        semantic = search_vectors(
            connection,
            batch.vectors[0],
            model=args.model,
            dimensions=args.dimensions,
            statuses=args.statuses,
            limit=args.limit,
        )
        results = merge_hybrid_results(lexical, semantic, limit=args.limit)
        _print_json(
            {
                "query": args.query,
                "mode": "hybrid",
                "api_inputs": 1,
                "prompt_tokens": batch.prompt_tokens,
                "total_tokens": batch.total_tokens,
                "results": results,
            }
        )
        return 0
    finally:
        connection.close()


def command_embed(args: argparse.Namespace) -> int:
    if args.limit < 1 or args.limit > MAX_LIVE_INPUTS:
        raise ValueError(f"--limit must be between 1 and {MAX_LIVE_INPUTS}")
    records = _records(args.data)
    connection = connect(args.db)
    try:
        index_records(connection, records)
        needed = records_needing_embeddings(
            connection, records, model=args.model, dimensions=args.dimensions
        )
        selected = needed[: args.limit]
        estimate = sum(max(1, (len(embedding_text(record)) + 3) // 4) for record in selected)
        plan = {
            "mode": "live" if args.live else "dry-run",
            "model": args.model,
            "dimensions": args.dimensions,
            "records_total": len(records),
            "records_stale_or_missing": len(needed),
            "records_selected": len(selected),
            "rough_input_token_estimate": estimate,
            "hard_live_input_cap": MAX_LIVE_INPUTS,
        }
        if not args.live or not selected:
            _print_json(plan)
            return 0
        texts = [embedding_text(record) for record in selected]
        reservation = reserve_paid_embedding_run(
            "record-embedding", texts, model=args.model, dimensions=args.dimensions
        )
        try:
            embedder = OpenAIEmbedder(model=args.model, dimensions=args.dimensions)
            batch = embedder.embed(texts)
            complete_paid_embedding_run(reservation, batch.prompt_tokens)
        except Exception as exc:
            fail_paid_embedding_run(reservation, type(exc).__name__)
            raise
        for record, vector in zip(selected, batch.vectors):
            put_embedding(
                connection,
                record["id"],
                args.model,
                args.dimensions,
                record_fingerprint(record, args.model, args.dimensions),
                vector,
            )
        plan.update(
            {
                "api_requests": 1,
                "prompt_tokens": batch.prompt_tokens,
                "total_tokens": batch.total_tokens,
            }
        )
        _print_json(plan)
        return 0
    finally:
        connection.close()


def command_smoke(args: argparse.Namespace) -> int:
    records = _records(args.fixture)
    if len(records) != 3:
        raise ValueError("the paid smoke test is fixed at exactly three fixture records")
    projected = [embedding_text(record) for record in records]
    plan = {
        "mode": "live" if args.live else "dry-run",
        "model": args.model,
        "dimensions": args.dimensions,
        "fixture_records": len(records),
        "query_inputs": 1,
        "api_requests": 1 if args.live else 0,
        "logical_provider_batches": 1,
        "provider_max_retries": 0,
        "api_inputs": len(records) + 1,
        "rough_input_token_estimate": sum(
            max(1, (len(text) + 3) // 4) for text in [*projected, SMOKE_QUERY]
        ),
    }
    if not args.live:
        _print_json(plan)
        return 0

    if Path(SMOKE_REPORT).exists():
        raise ValueError(
            f"the one authorized live smoke call is already recorded at {SMOKE_REPORT}"
        )
    if Path(args.fixture).resolve() != Path(DEFAULT_FIXTURE).resolve():
        raise ValueError("live smoke fixture is fixed; arbitrary paid fixtures are not allowed")
    if args.model != DEFAULT_MODEL or args.dimensions != DEFAULT_DIMENSIONS:
        raise ValueError("live smoke model and dimensions are fixed")
    live_texts = [*projected, SMOKE_QUERY]
    if len(live_texts) != 4 or sum(len(text.encode("utf-8")) for text in live_texts) > 20_000:
        raise ValueError("live smoke input exceeds its fixed safety envelope")

    connection = connect(args.db)
    try:
        index_records(connection, records)
        reservation = reserve_paid_embedding_run(
            "embedding-smoke",
            live_texts,
            model=args.model,
            dimensions=args.dimensions,
        )
        try:
            embedder = OpenAIEmbedder(model=args.model, dimensions=args.dimensions)
            # One logical batch, with SDK retries disabled by OpenAIEmbedder.
            batch = embedder.embed(live_texts)
        except Exception as exc:
            fail_paid_embedding_run(reservation, type(exc).__name__)
            raise
        complete_paid_embedding_run(reservation, batch.prompt_tokens)
        for record, vector in zip(records, batch.vectors[:3]):
            put_embedding(
                connection,
                record["id"],
                args.model,
                args.dimensions,
                record_fingerprint(record, args.model, args.dimensions),
                vector,
            )
        ranking = search_vectors(
            connection,
            batch.vectors[3],
            model=args.model,
            dimensions=args.dimensions,
            statuses=("candidate",),
            limit=3,
        )
    finally:
        connection.close()

    manifest = {
        **plan,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "prompt_tokens": batch.prompt_tokens,
        "total_tokens": batch.total_tokens,
        "result_ids": [item["id"] for item in ranking],
        "scores": {item["id"]: item["semantic_score"] for item in ranking},
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _print_json({**manifest, "manifest": str(manifest_path), "database": args.db})
    return 0


def command_pilot_embedding_evaluation(args: argparse.Namespace) -> int:
    records = _records(args.data)
    findings = [
        *evaluate_pilot_compositions(records),
        *evaluate_anchor_chorus_compositions(records),
        *evaluate_perception_compositions(records),
        *evaluate_static_place_compositions(records),
        *evaluate_motion_action_compositions(records),
    ]
    if findings:
        raise ValueError("pilot composition checks failed: " + "; ".join(findings))
    queries = load_semantic_queries(args.queries)
    record_ids = [record["id"] for record in records]
    unknown_targets = sorted(
        {query["expected_id"] for query in queries} - set(record_ids)
    )
    if unknown_targets:
        raise ValueError(f"semantic queries target unknown records: {unknown_targets}")

    projected = [embedding_text(record) for record in records]
    live_texts = [*projected, *(query["query"] for query in queries)]
    policy = load_policy()
    byte_count = sum(len(text.encode("utf-8")) for text in live_texts)
    largest_input_bytes = max(len(text.encode("utf-8")) for text in live_texts)
    if largest_input_bytes > N1_CORE_MAX_INPUT_BYTES:
        raise ValueError(
            "an embedding input exceeds the conservative per-input provider safety cap"
        )
    conservative_tokens = token_upper_bound(live_texts)
    rough_tokens = sum(max(1, (len(text) + 3) // 4) for text in live_texts)
    price = float(policy["price_per_million_input_tokens_usd"])
    plan = {
        "mode": "live" if args.live else "dry-run",
        "evaluation_kind": "retrieval_sanity_test",
        "model": args.model,
        "dimensions": args.dimensions,
        "records": len(records),
        "queries": len(queries),
        "api_inputs": len(live_texts),
        "api_requests": 1 if args.live else 0,
        "utf8_bytes": byte_count,
        "largest_input_utf8_bytes": largest_input_bytes,
        "conservative_per_input_byte_cap": N1_CORE_MAX_INPUT_BYTES,
        "rough_input_token_estimate": rough_tokens,
        "conservative_token_upper_bound": conservative_tokens,
        "conservative_cost_upper_bound_usd": conservative_tokens * price / 1_000_000,
        "authorized_cumulative_cost_cap_usd": policy["max_estimated_cost_usd"],
        "predeclared_pass_criteria": {"minimum_recall_at_3": 1.0},
        "metric_resolution": 1.0 / len(queries),
        "limitations": (
            "Five project-authored paraphrases test the retrieval pipeline over candidate "
            "records. They are not an unbiased benchmark and cannot detect linguistic conflict."
        ),
    }
    if not args.live:
        _print_json(plan)
        return 0

    fixed_paths = {
        "data": (Path(args.data).resolve(), Path(DEFAULT_PILOT_DATA).resolve()),
        "queries": (Path(args.queries).resolve(), Path(DEFAULT_PILOT_QUERIES).resolve()),
        "report": (Path(args.report).resolve(), Path(PILOT_EMBEDDING_REPORT).resolve()),
    }
    for label, (actual, expected) in fixed_paths.items():
        if actual != expected:
            raise ValueError(f"live pilot {label} path is fixed at {expected}")
    if Path(args.report).exists():
        raise ValueError(f"the bounded pilot call is already recorded at {args.report}")
    if args.model != DEFAULT_MODEL or args.dimensions != DEFAULT_DIMENSIONS:
        raise ValueError("live pilot model and dimensions are fixed")
    if len(records) != 20 or len(queries) != 5 or len(live_texts) != PILOT_LIVE_INPUTS:
        raise ValueError("live pilot envelope is fixed at 20 records and 5 queries")

    reservation = reserve_paid_embedding_run(
        "n1-pilot-embedding-evaluation",
        live_texts,
        model=args.model,
        dimensions=args.dimensions,
    )
    try:
        embedder = OpenAIEmbedder(model=args.model, dimensions=args.dimensions)
        # All records and frozen queries share one request, so this command cannot
        # quietly multiply provider calls when the evaluation set grows.
        batch = embedder.embed(live_texts)
        complete_paid_embedding_run(reservation, batch.prompt_tokens)
    except Exception as exc:
        fail_paid_embedding_run(reservation, type(exc).__name__)
        raise

    record_vectors = batch.vectors[: len(records)]
    query_vectors = batch.vectors[len(records) :]
    evaluation = evaluate_semantic_rankings(
        record_ids,
        record_vectors,
        queries,
        query_vectors,
    )
    evaluation["passed"] = evaluation["recall_at_3"] >= 1.0

    connection = connect(args.db)
    try:
        index_records(connection, records)
        for record, vector in zip(records, record_vectors):
            put_embedding(
                connection,
                record["id"],
                args.model,
                args.dimensions,
                record_fingerprint(record, args.model, args.dimensions),
                vector,
            )
    finally:
        connection.close()

    report = {
        **plan,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "data": args.data,
        "query_fixture": args.queries,
        "data_sha256": hashlib.sha256(Path(args.data).read_bytes()).hexdigest(),
        "query_fixture_sha256": hashlib.sha256(
            Path(args.queries).read_bytes()
        ).hexdigest(),
        "ledger_run_id": reservation.run_id,
        "prompt_tokens": batch.prompt_tokens,
        "total_tokens": batch.total_tokens,
        "estimated_cost_usd": batch.prompt_tokens * price / 1_000_000,
        "record_revisions": {record["id"]: record["revision"] for record in records},
        "evaluation": evaluation,
        "interpretation": (
            "Diagnostic retrieval results over candidate records; they do not validate "
            "the language forms or promote any record toward canon."
        ),
        "contains_vectors": False,
        "contains_credentials": False,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _print_json(
        {
            **plan,
            "prompt_tokens": batch.prompt_tokens,
            "estimated_cost_usd": report["estimated_cost_usd"],
            "evaluation": evaluation,
            "report": str(report_path),
            "database": args.db,
        }
    )
    return 0


def _data_tree_manifest(path: str | Path) -> tuple[str, dict[str, str]]:
    root = Path(path)
    files = [root] if root.is_file() else sorted(root.rglob("*.jsonl"))
    if not files:
        raise ValueError(f"{path}: no JSONL data files found")
    aggregate = hashlib.sha256()
    hashes: dict[str, str] = {}
    for candidate in files:
        relative = candidate.name if root.is_file() else candidate.relative_to(root).as_posix()
        content = candidate.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        hashes[relative] = digest
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(content)
        aggregate.update(b"\0")
    return aggregate.hexdigest(), hashes


def command_n1_core_embedding_evaluation(args: argparse.Namespace) -> int:
    """Plan or consume the single frozen N1 core embedding checkpoint."""

    records = _records(args.data)
    findings = [
        *evaluate_pilot_compositions(records),
        *evaluate_anchor_chorus_compositions(records),
        *evaluate_perception_compositions(records),
        *evaluate_static_place_compositions(records),
        *evaluate_motion_action_compositions(records),
    ]
    if findings:
        raise ValueError("N1 composition checks failed: " + "; ".join(findings))
    queries = load_semantic_queries(args.queries)
    record_ids = [record["id"] for record in records]
    unknown_targets = sorted(
        {query["expected_id"] for query in queries} - set(record_ids)
    )
    if unknown_targets:
        raise ValueError(f"semantic queries target unknown records: {unknown_targets}")

    projected = [embedding_text(record) for record in records]
    live_texts = [*projected, *(query["query"] for query in queries)]
    policy = load_policy()
    byte_count = sum(len(text.encode("utf-8")) for text in live_texts)
    largest_input_bytes = max(len(text.encode("utf-8")) for text in live_texts)
    if largest_input_bytes > N1_CORE_MAX_INPUT_BYTES:
        raise ValueError(
            "an embedding input exceeds the conservative per-input provider safety cap"
        )
    conservative_tokens = token_upper_bound(live_texts)
    rough_tokens = sum(max(1, (len(text) + 3) // 4) for text in live_texts)
    price = float(policy["price_per_million_input_tokens_usd"])
    data_hash, data_file_hashes = _data_tree_manifest(args.data)
    query_hash = hashlib.sha256(Path(args.queries).read_bytes()).hexdigest()
    plan = {
        "mode": "live" if args.live else "dry-run",
        "evaluation_kind": "bounded_n1_core_retrieval_checkpoint",
        "model": args.model,
        "dimensions": args.dimensions,
        "records": len(records),
        "queries": len(queries),
        "api_inputs": len(live_texts),
        "api_requests": 1 if args.live else 0,
        "utf8_bytes": byte_count,
        "largest_input_utf8_bytes": largest_input_bytes,
        "conservative_per_input_byte_cap": N1_CORE_MAX_INPUT_BYTES,
        "rough_input_token_estimate": rough_tokens,
        "conservative_token_upper_bound": conservative_tokens,
        "conservative_cost_upper_bound_usd": conservative_tokens * price / 1_000_000,
        "authorized_cumulative_cost_cap_usd": policy["max_estimated_cost_usd"],
        "predeclared_pass_criteria": {"minimum_recall_at_3": 0.8},
        "metric_resolution": 1.0 / len(queries),
        "data_sha256": data_hash,
        "data_file_sha256": data_file_hashes,
        "query_fixture_sha256": query_hash,
        "limitations": (
            "Twelve project-authored paraphrases test retrieval plumbing over a bounded "
            "candidate set. They are not an independent linguistic benchmark and do not "
            "promote any record toward canon."
        ),
    }
    if not args.live:
        _print_json(plan)
        return 0

    fixed_paths = {
        "data": (Path(args.data).resolve(), Path(DEFAULT_N1_CORE_DATA).resolve()),
        "queries": (
            Path(args.queries).resolve(),
            Path(DEFAULT_N1_CORE_QUERIES).resolve(),
        ),
        "report": (
            Path(args.report).resolve(),
            Path(N1_CORE_EMBEDDING_REPORT).resolve(),
        ),
        "database": (Path(args.db).resolve(), Path(DEFAULT_N1_CORE_DB).resolve()),
    }
    for label, (actual, expected) in fixed_paths.items():
        if actual != expected:
            raise ValueError(f"live N1 core {label} path is fixed at {expected}")
    if Path(args.report).exists():
        raise ValueError(f"the bounded N1 core call is already recorded at {args.report}")
    if args.model != DEFAULT_MODEL or args.dimensions != DEFAULT_DIMENSIONS:
        raise ValueError("live N1 core model and dimensions are fixed")
    if (
        len(records) != N1_CORE_RECORDS
        or len(queries) != N1_CORE_QUERIES
        or len(live_texts) != N1_CORE_LIVE_INPUTS
    ):
        raise ValueError(
            "live N1 core envelope is fixed at 92 records and 12 queries"
        )

    connection = connect(args.db)
    try:
        index_records(connection, records)
        needed = records_needing_embeddings(
            connection,
            records,
            model=args.model,
            dimensions=args.dimensions,
        )
        if {record["id"] for record in needed} != set(record_ids):
            raise ValueError(
                "live N1 core database must begin with every frozen record stale or missing"
            )

        reservation = reserve_paid_embedding_run(
            "n1-core-embedding-evaluation",
            live_texts,
            model=args.model,
            dimensions=args.dimensions,
        )
        try:
            embedder = OpenAIEmbedder(model=args.model, dimensions=args.dimensions)
            batch = embedder.embed(live_texts)
            complete_paid_embedding_run(reservation, batch.prompt_tokens)
        except Exception as exc:
            fail_paid_embedding_run(reservation, type(exc).__name__)
            raise

        record_vectors = batch.vectors[: len(records)]
        query_vectors = batch.vectors[len(records) :]
        evaluation = evaluate_semantic_rankings(
            record_ids,
            record_vectors,
            queries,
            query_vectors,
        )
        evaluation["passed"] = evaluation["recall_at_3"] >= 0.8
        for record, vector in zip(records, record_vectors):
            put_embedding(
                connection,
                record["id"],
                args.model,
                args.dimensions,
                record_fingerprint(record, args.model, args.dimensions),
                vector,
            )
    finally:
        connection.close()

    report = {
        **plan,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "data": args.data,
        "query_fixture": args.queries,
        "ledger_run_id": reservation.run_id,
        "prompt_tokens": batch.prompt_tokens,
        "total_tokens": batch.total_tokens,
        "estimated_cost_usd": batch.prompt_tokens * price / 1_000_000,
        "record_revisions": {record["id"]: record["revision"] for record in records},
        "evaluation": evaluation,
        "interpretation": (
            "A bounded diagnostic of search behavior over noncanonical records; source "
            "review and language-design review remain independent gates."
        ),
        "contains_vectors": False,
        "contains_credentials": False,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _print_json(
        {
            **plan,
            "prompt_tokens": batch.prompt_tokens,
            "estimated_cost_usd": report["estimated_cost_usd"],
            "evaluation": evaluation,
            "report": str(report_path),
            "database": args.db,
        }
    )
    return 0


def command_static_place_embedding_evaluation(args: argparse.Namespace) -> int:
    """Report or consume the one-shot semantic bootstrap over the frozen corpus."""

    fixed_paths = {
        "data": (Path(args.data).resolve(), Path(DEFAULT_N1_CORE_DATA).resolve()),
        "queries": (
            Path(args.queries).resolve(),
            Path(DEFAULT_STATIC_PLACE_QUERIES).resolve(),
        ),
        "report": (
            Path(args.report).resolve(),
            Path(STATIC_PLACE_EMBEDDING_REPORT).resolve(),
        ),
        "database": (
            Path(args.db).resolve(),
            Path(DEFAULT_STATIC_PLACE_DB).resolve(),
        ),
    }
    for label, (actual, expected) in fixed_paths.items():
        if actual != expected:
            raise ValueError(f"static-place checkpoint {label} path is fixed at {expected}")
    if args.model != DEFAULT_MODEL or args.dimensions != DEFAULT_DIMENSIONS:
        raise ValueError("static-place checkpoint model and dimensions are fixed")

    report_path = Path(args.report)
    if report_path.exists():
        if args.live:
            raise ValueError(
                "the scoped static-place authorization is already consumed; "
                f"its historical checkpoint is recorded at {args.report}"
            )
        historical = json.loads(report_path.read_text(encoding="utf-8"))
        expected_history = {
            "evaluation_kind": "static_place_living_index_bootstrap",
            "records": STATIC_PLACE_RECORDS,
            "queries": STATIC_PLACE_QUERIES,
            "data_sha256": STATIC_PLACE_EXPECTED_DATA_SHA256,
            "query_fixture_sha256": STATIC_PLACE_EXPECTED_QUERY_SHA256,
        }
        evaluation = historical.get("evaluation") if isinstance(historical, dict) else None
        by_query_type = evaluation.get("by_query_type") if isinstance(evaluation, dict) else None
        query_types = {"english", "conlang", "compositional", "contrastive"}
        if (
            not isinstance(historical, dict)
            or any(historical.get(key) != value for key, value in expected_history.items())
            or not historical.get("completed_at")
            or not historical.get("ledger_run_id")
            or historical.get("contains_vectors") is not False
            or historical.get("contains_credentials") is not False
            or not isinstance(evaluation, dict)
            or not isinstance(by_query_type, dict)
            or set(by_query_type) != query_types
            or any(
                not isinstance(evaluation.get(key), (int, float))
                for key in ("recall_at_1", "recall_at_3", "mean_reciprocal_rank")
            )
            or not isinstance(evaluation.get("passed"), bool)
        ):
            raise ValueError(
                "the recorded static-place checkpoint is malformed or does not "
                f"match its frozen envelope: {args.report}"
            )
        historical_summary = {
            key: historical[key]
            for key in (
                "completed_at",
                "mode",
                "evaluation_kind",
                "model",
                "dimensions",
                "records",
                "queries",
                "api_inputs",
                "prompt_tokens",
                "estimated_new_cost_usd",
                "fresh_record_vectors",
                "data_sha256",
                "query_fixture_sha256",
                "contains_vectors",
                "contains_credentials",
            )
        }
        historical_summary.update(
            {
                "logical_provider_batches": historical["planned_provider_requests"],
                "http_attempts_instrumented": False,
                "sdk_default_max_retries_at_run": 2,
                "evaluation": {
                    "recall_at_1": evaluation["recall_at_1"],
                    "recall_at_3": evaluation["recall_at_3"],
                    "mean_reciprocal_rank": evaluation["mean_reciprocal_rank"],
                    "passed": evaluation["passed"],
                    "by_query_type": {
                        query_type: {
                            key: by_query_type[query_type][key]
                            for key in (
                                "query_count",
                                "recall_at_1",
                                "recall_at_3",
                                "mean_reciprocal_rank",
                            )
                        }
                        for query_type in sorted(query_types)
                    },
                },
            }
        )
        _print_json(
            {
                "mode": "historical-report",
                "checkpoint_status": "consumed",
                "api_requests": 0,
                "current_records": len(_records(args.data)),
                "report": str(report_path),
                "historical_checkpoint": historical_summary,
            }
        )
        return 0

    records = _records(args.data)
    findings = [
        *evaluate_pilot_compositions(records),
        *evaluate_anchor_chorus_compositions(records),
        *evaluate_perception_compositions(records),
        *evaluate_static_place_compositions(records),
        *evaluate_motion_action_compositions(records),
    ]
    if findings:
        raise ValueError("static-place composition checks failed: " + "; ".join(findings))
    queries = load_typed_semantic_queries(args.queries)
    record_ids = [record["id"] for record in records]
    known_ids = set(record_ids)
    unknown_targets = sorted(
        {
            target
            for query in queries
            for target in query["acceptable_ids"]
            if target not in known_ids
        }
    )
    if unknown_targets:
        raise ValueError(f"typed semantic queries target unknown records: {unknown_targets}")

    data_hash, data_file_hashes = _data_tree_manifest(args.data)
    query_hash = hashlib.sha256(Path(args.queries).read_bytes()).hexdigest()
    if len(records) != STATIC_PLACE_RECORDS or len(queries) != STATIC_PLACE_QUERIES:
        raise ValueError(
            "static-place checkpoint envelope is fixed at 180 records and 16 queries"
        )
    if data_hash != STATIC_PLACE_EXPECTED_DATA_SHA256:
        raise ValueError("static-place checkpoint data hash no longer matches its frozen corpus")
    if query_hash != STATIC_PLACE_EXPECTED_QUERY_SHA256:
        raise ValueError("static-place checkpoint query hash no longer matches its frozen fixture")

    projected = [embedding_text(record) for record in records]
    query_texts = [query["query"] for query in queries]
    live_texts = [*projected, *query_texts]
    descriptors = [
        *(f"record:{record_id}" for record_id in record_ids),
        *(f"query:{query['id']}" for query in queries),
    ]
    policy = load_policy()
    batches = _chunk_embedding_inputs(
        live_texts,
        max_inputs=policy["max_inputs_per_run"],
        max_utf8_bytes=policy["max_utf8_bytes_per_run"],
        max_input_utf8_bytes=policy.get("max_input_utf8_bytes", N1_CORE_MAX_INPUT_BYTES),
    )
    if len(batches) != 2:
        raise ValueError("the frozen static-place checkpoint must plan exactly two requests")
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for batch in batches:
        offsets.append((cursor, cursor + len(batch)))
        cursor += len(batch)
    price = float(policy["price_per_million_input_tokens_usd"])
    conservative_tokens = token_upper_bound(live_texts)
    rough_tokens = sum(max(1, (len(text_value) + 3) // 4) for text_value in live_texts)
    accounting = budget_snapshot()
    projected_cumulative = (
        int(accounting["cumulative_accounted_input_tokens"]) + conservative_tokens
    )
    batch_manifest = [
        {
            "batch": index,
            "input_count": len(batch),
            "utf8_bytes": token_upper_bound(batch),
            "first_input": descriptors[start],
            "last_input": descriptors[end - 1],
        }
        for index, (batch, (start, end)) in enumerate(zip(batches, offsets), start=1)
    ]
    plan = {
        "mode": "live" if args.live else "dry-run",
        "evaluation_kind": "static_place_living_index_bootstrap",
        "authorization_id": policy.get("authorization_id"),
        "model": args.model,
        "dimensions": args.dimensions,
        "records": len(records),
        "queries": len(queries),
        "query_types": {
            query_type: sum(query["query_type"] == query_type for query in queries)
            for query_type in ("english", "conlang", "compositional", "contrastive")
        },
        "api_inputs": len(live_texts),
        "api_requests": len(batches) if args.live else 0,
        "planned_provider_requests": len(batches),
        "logical_provider_batches": len(batches),
        "provider_max_retries": 0,
        "planned_batches": batch_manifest,
        "utf8_bytes": token_upper_bound(live_texts),
        "largest_input_utf8_bytes": max(len(value.encode("utf-8")) for value in live_texts),
        "rough_input_token_estimate": rough_tokens,
        "conservative_token_upper_bound": conservative_tokens,
        "new_checkpoint_conservative_cost_upper_bound_usd": conservative_tokens
        * price
        / 1_000_000,
        "historical_budget_accounting": accounting,
        "projected_cumulative_conservative_tokens": projected_cumulative,
        "projected_cumulative_conservative_cost_usd": projected_cumulative
        * price
        / 1_000_000,
        "authorized_cumulative_token_cap": policy["max_total_input_tokens"],
        "authorized_cumulative_cost_cap_usd": policy["max_estimated_cost_usd"],
        "predeclared_pass_criteria": {
            "minimum_overall_recall_at_3": 0.75,
            "minimum_each_query_type_recall_at_3": 0.5,
        },
        "data_sha256": data_hash,
        "data_file_sha256": data_file_hashes,
        "query_fixture_sha256": query_hash,
        "limitations": (
            "Sixteen project-authored diagnostics test English, contact-language, "
            "compositional, and contrastive retrieval. They are not independent "
            "linguistic evidence, do not train the embedding model, and cannot promote records."
        ),
    }
    if not args.live:
        _print_json(plan)
        return 0

    connection = connect(args.db)
    try:
        index_records(connection, records)
        needed = records_needing_embeddings(
            connection,
            records,
            model=args.model,
            dimensions=args.dimensions,
        )
        if {record["id"] for record in needed} != set(record_ids):
            raise ValueError(
                "the static-place checkpoint database must begin with all 180 "
                "vectors missing or stale"
            )

        reservation = reserve_paid_embedding_checkpoint(
            STATIC_PLACE_RUN_KIND,
            batches,
            model=args.model,
            dimensions=args.dimensions,
        )
        vectors: list[list[float]] = []
        prompt_tokens = 0
        total_tokens = 0
        batch_usage: list[dict[str, int]] = []
        try:
            embedder = OpenAIEmbedder(model=args.model, dimensions=args.dimensions)
            for index, batch_texts in enumerate(batches, start=1):
                batch = embedder.embed(batch_texts)
                vectors.extend(batch.vectors)
                prompt_tokens += batch.prompt_tokens
                total_tokens += batch.total_tokens
                batch_usage.append(
                    {
                        "batch": index,
                        "input_count": len(batch_texts),
                        "prompt_tokens": batch.prompt_tokens,
                        "total_tokens": batch.total_tokens,
                    }
                )
            complete_paid_embedding_run(reservation, prompt_tokens)
        except Exception as exc:
            fail_paid_embedding_run(reservation, type(exc).__name__)
            raise

        record_vectors = vectors[: len(records)]
        query_vectors = vectors[len(records) :]
        if len(query_vectors) != len(queries):
            raise RuntimeError("static-place checkpoint vector reassembly failed")
        evaluation = evaluate_semantic_rankings(
            record_ids,
            record_vectors,
            queries,
            query_vectors,
        )
        type_metrics = evaluation.get("by_query_type", {})
        evaluation["passed"] = (
            evaluation["recall_at_3"] >= 0.75
            and all(
                metrics["recall_at_3"] >= 0.5
                for metrics in type_metrics.values()
            )
            and set(type_metrics)
            == {"english", "conlang", "compositional", "contrastive"}
        )
        put_embeddings_atomic(
            connection,
            [
                (
                    record["id"],
                    args.model,
                    args.dimensions,
                    record_fingerprint(record, args.model, args.dimensions),
                    vector,
                )
                for record, vector in zip(records, record_vectors)
            ],
        )
        fresh_count = count_fresh_embeddings(
            connection,
            model=args.model,
            dimensions=args.dimensions,
        )
        if fresh_count != len(records):
            raise RuntimeError("static-place checkpoint did not persist all fresh record vectors")
    finally:
        connection.close()

    report = {
        **plan,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "data": args.data,
        "query_fixture": args.queries,
        "ledger_run_id": reservation.run_id,
        "ledger_authorization_id": reservation.authorization_id,
        "batch_usage": batch_usage,
        "prompt_tokens": prompt_tokens,
        "total_tokens": total_tokens,
        "estimated_new_cost_usd": prompt_tokens * price / 1_000_000,
        "record_revisions": {record["id"]: record["revision"] for record in records},
        "evaluation": evaluation,
        "fresh_record_vectors": fresh_count,
        "database_sha256": hashlib.sha256(Path(args.db).read_bytes()).hexdigest(),
        "interpretation": (
            "A one-shot diagnostic of retrieval over noncanonical records. The vectors "
            "are a local search aid only; manual source and language-design review remain decisive."
        ),
        "contains_vectors": False,
        "contains_credentials": False,
    }
    _write_json_atomic(args.report, report)
    _print_json(
        {
            **plan,
            "prompt_tokens": prompt_tokens,
            "estimated_new_cost_usd": report["estimated_new_cost_usd"],
            "evaluation": evaluation,
            "fresh_record_vectors": fresh_count,
            "report": args.report,
            "database": args.db,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="judeoalgonquin",
        description="Validate, index, and search the Judeo-Algonquin knowledge base.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate canonical JSONL")
    validate.add_argument("--data", default=DEFAULT_DATA)
    validate.set_defaults(func=command_validate)

    validate_anchors = subparsers.add_parser(
        "validate-anchors",
        help="validate creative-anchor continuity ledgers and language-record links",
    )
    validate_anchors.add_argument("--anchors", default=DEFAULT_ANCHORS)
    validate_anchors.add_argument("--data", default=DEFAULT_DATA)
    validate_anchors.set_defaults(func=command_validate_anchors)

    build = subparsers.add_parser("build", help="build or refresh the local SQLite index")
    build.add_argument("--data", default=DEFAULT_DATA)
    build.add_argument("--db", default=DEFAULT_DB)
    build.set_defaults(func=command_build)

    evaluate = subparsers.add_parser(
        "evaluate", help="run deterministic composition checks over validated records"
    )
    evaluate.add_argument("--data", default=DEFAULT_PILOT_DATA)
    evaluate.set_defaults(func=command_evaluate)

    search = subparsers.add_parser("search", help="search a built local index")
    search.add_argument("query")
    search.add_argument("--db", default=DEFAULT_DB)
    search.add_argument("--limit", type=int, default=10)
    search.add_argument(
        "--statuses", type=_statuses, default=("candidate", "reviewed", "canonical")
    )
    search.add_argument("--semantic", action="store_true")
    search.add_argument("--live", action="store_true")
    search.add_argument("--model", default=DEFAULT_MODEL)
    search.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    search.set_defaults(func=command_search)

    embed = subparsers.add_parser("embed", help="plan or perform capped incremental embedding")
    embed.add_argument("--data", default=DEFAULT_DATA)
    embed.add_argument("--db", default=DEFAULT_DB)
    embed.add_argument("--model", default=DEFAULT_MODEL)
    embed.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    embed.add_argument("--limit", type=int, default=10)
    embed.add_argument("--live", action="store_true")
    embed.set_defaults(func=command_embed)

    smoke = subparsers.add_parser(
        "smoke", help="plan or run the single-request paid embeddings smoke test"
    )
    smoke.add_argument("--fixture", default=DEFAULT_FIXTURE)
    smoke.add_argument("--db", default=DEFAULT_SMOKE_DB)
    smoke.add_argument("--manifest", default=DEFAULT_SMOKE_MANIFEST)
    smoke.add_argument("--model", default=DEFAULT_MODEL)
    smoke.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    smoke.add_argument("--live", action="store_true")
    smoke.set_defaults(func=command_smoke)

    pilot = subparsers.add_parser(
        "pilot-embedding-eval",
        help="plan or run the fixed one-request N1 semantic retrieval evaluation",
    )
    pilot.add_argument("--data", default=DEFAULT_PILOT_DATA)
    pilot.add_argument("--queries", default=DEFAULT_PILOT_QUERIES)
    pilot.add_argument("--db", default=DEFAULT_PILOT_DB)
    pilot.add_argument("--report", default=PILOT_EMBEDDING_REPORT)
    pilot.add_argument("--model", default=DEFAULT_MODEL)
    pilot.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    pilot.add_argument("--live", action="store_true")
    pilot.set_defaults(func=command_pilot_embedding_evaluation)

    n1_core = subparsers.add_parser(
        "n1-core-embedding-eval",
        help="plan or run the frozen one-request N1 core retrieval checkpoint",
    )
    n1_core.add_argument("--data", default=DEFAULT_N1_CORE_DATA)
    n1_core.add_argument("--queries", default=DEFAULT_N1_CORE_QUERIES)
    n1_core.add_argument("--db", default=DEFAULT_N1_CORE_DB)
    n1_core.add_argument("--report", default=N1_CORE_EMBEDDING_REPORT)
    n1_core.add_argument("--model", default=DEFAULT_MODEL)
    n1_core.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    n1_core.add_argument("--live", action="store_true")
    n1_core.set_defaults(func=command_n1_core_embedding_evaluation)

    static_place = subparsers.add_parser(
        "static-place-embedding-eval",
        help="plan or run the frozen two-request static-place semantic bootstrap",
    )
    static_place.add_argument("--data", default=DEFAULT_N1_CORE_DATA)
    static_place.add_argument("--queries", default=DEFAULT_STATIC_PLACE_QUERIES)
    static_place.add_argument("--db", default=DEFAULT_STATIC_PLACE_DB)
    static_place.add_argument("--report", default=STATIC_PLACE_EMBEDDING_REPORT)
    static_place.add_argument("--model", default=DEFAULT_MODEL)
    static_place.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    static_place.add_argument("--live", action="store_true")
    static_place.set_defaults(func=command_static_place_embedding_evaluation)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ValidationError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        # Live provider exceptions can contain request metadata. Do not echo them because
        # credentials must never leak through CLI error handling.
        if getattr(args, "live", False):
            print(
                f"error: live API action failed ({type(exc).__name__}); "
                "check credentials, quota, network access, and the provider dashboard",
                file=sys.stderr,
            )
            return 3
        raise


if __name__ == "__main__":
    raise SystemExit(main())
