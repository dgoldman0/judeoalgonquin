"""Command-line entry point. All paid actions are explicit and capped."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .budget import (
    complete_paid_embedding_run,
    fail_paid_embedding_run,
    reserve_paid_embedding_run,
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
    load_source_registry_ids,
    validate_records,
)
from .store import (
    connect,
    count_fresh_embeddings,
    index_records,
    merge_hybrid_results,
    put_embedding,
    search_text,
    search_vectors,
)


DEFAULT_DATA = "data/entries"
DEFAULT_DB = ".local/judeoalgonquin.sqlite3"
DEFAULT_FIXTURE = "tests/fixtures/creative_anchor_candidates.jsonl"
DEFAULT_SMOKE_DB = ".local/embedding-smoke.sqlite3"
DEFAULT_SMOKE_MANIFEST = ".local/embedding-smoke-manifest.json"
SMOKE_REPORT = "docs/reports/embedding-smoke-2026-07-12.json"
SOURCE_REGISTRY = "references/sources.yaml"
SMOKE_QUERY = "home, dwelling, and the place where people live together"


def _records(path: str) -> list[dict[str, Any]]:
    source_ids = load_source_registry_ids(SOURCE_REGISTRY)
    return validate_records(load_records(path), source_registry_ids=source_ids)


def _statuses(value: str) -> tuple[str, ...]:
    statuses = tuple(part.strip() for part in value.split(",") if part.strip())
    allowed = {"candidate", "reviewed", "canonical", "deprecated", "rejected"}
    if not statuses or not set(statuses) <= allowed:
        raise argparse.ArgumentTypeError("invalid comma-separated status list")
    return statuses


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def command_validate(args: argparse.Namespace) -> int:
    records = _records(args.data)
    _print_json({"valid": True, "records": len(records), "data": args.data})
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
        reservation = reserve_paid_embedding_run("semantic-search", texts)
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
        reservation = reserve_paid_embedding_run("record-embedding", texts)
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
        embedder = OpenAIEmbedder(model=args.model, dimensions=args.dimensions)
        # Deliberately one request: three records and the query are a single input batch.
        batch = embedder.embed(live_texts)
        for record, text, vector in zip(records, projected, batch.vectors[:3]):
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="judeoalgonquin",
        description="Validate, index, and search the Judeo-Algonquin knowledge base.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate canonical JSONL")
    validate.add_argument("--data", default=DEFAULT_DATA)
    validate.set_defaults(func=command_validate)

    build = subparsers.add_parser("build", help="build or refresh the local SQLite index")
    build.add_argument("--data", default=DEFAULT_DATA)
    build.add_argument("--db", default=DEFAULT_DB)
    build.set_defaults(func=command_build)

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
