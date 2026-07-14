import hashlib
import io
import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from judeoalgonquin.cli import (
    DEFAULT_DIMENSIONS,
    DEFAULT_MODEL,
    MOTION_ACTION_DATA_FILES,
    MOTION_ACTION_EXPECTED_DATA_SHA256,
    MOTION_ACTION_EXPECTED_QUERY_SHA256,
    MOTION_ACTION_EXPECTED_RECORD_REVISIONS_SHA256,
    MOTION_ACTION_RUN_KIND,
    STATIC_PLACE_DATA_FILES,
    _frozen_motion_action_split,
    _records_from_named_files,
    main,
)
from judeoalgonquin.embeddings import EmbeddingBatch
from judeoalgonquin.evaluate import (
    evaluate_semantic_rankings as real_evaluate_semantic_rankings,
    load_typed_semantic_queries,
)


ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "entries"
QUERIES = ROOT / "tests" / "fixtures" / "motion_action_semantic_queries.json"
BASE_DB = ROOT / ".local" / "static-place-semantic-bootstrap.sqlite3"
POLICY = ROOT / "config" / "api-budget.json"


class FakeOneShotEmbedder:
    def __init__(self, *, model: str, dimensions: int) -> None:
        self.model = model
        self.dimensions = dimensions
        self.calls: list[list[str]] = []

    def embed(self, texts):
        captured = list(texts)
        self.calls.append(captured)
        vectors = []
        for index, _ in enumerate(captured):
            vector = [0.0] * self.dimensions
            vector[index % self.dimensions] = 1.0
            vectors.append(vector)
        return EmbeddingBatch(
            vectors=vectors,
            prompt_tokens=len(captured),
            total_tokens=len(captured),
        )


class MotionActionCheckpointTests(unittest.TestCase):
    def _copy_base(self, directory: Path) -> Path:
        target = directory / "living.sqlite3"
        shutil.copy2(BASE_DB, target)
        return target

    def _live_patches(self, db: Path, report: Path, embedder: FakeOneShotEmbedder):
        reservation = SimpleNamespace(
            run_id="unit-test-run",
            authorization_id="unit-test-authorization",
        )
        return (
            patch("judeoalgonquin.cli.DEFAULT_STATIC_PLACE_DB", str(db)),
            patch("judeoalgonquin.cli.MOTION_ACTION_EMBEDDING_REPORT", str(report)),
            patch(
                "judeoalgonquin.cli.reserve_paid_embedding_checkpoint",
                return_value=reservation,
            ),
            patch("judeoalgonquin.cli.complete_paid_embedding_run"),
            patch("judeoalgonquin.cli.fail_paid_embedding_run"),
            patch("judeoalgonquin.cli.OpenAIEmbedder", return_value=embedder),
        )

    def test_frozen_selection_and_balanced_queries_match_hashes(self) -> None:
        frozen_files = (*STATIC_PLACE_DATA_FILES, *MOTION_ACTION_DATA_FILES)
        records = _records_from_named_files(DATA, frozen_files)
        (
            base,
            motion,
            base_hash,
            _,
            motion_hash,
            _,
            revision_hash,
        ) = _frozen_motion_action_split(DATA, records)
        self.assertEqual((len(base), len(motion), len(records)), (180, 45, 225))
        self.assertEqual(
            len({record["id"] for record in motion}),
            45,
        )
        self.assertEqual(
            base_hash,
            "2af1fd2ad2976aea64b9e7a1281b04a3a3fefd5f56b6d07f5ccaa6a7b3c37f60",
        )
        self.assertEqual(motion_hash, MOTION_ACTION_EXPECTED_DATA_SHA256)
        self.assertEqual(
            revision_hash, MOTION_ACTION_EXPECTED_RECORD_REVISIONS_SHA256
        )

        queries = load_typed_semantic_queries(QUERIES)
        self.assertEqual(len(queries), 12)
        self.assertEqual(
            {
                query_type: sum(
                    query["query_type"] == query_type for query in queries
                )
                for query_type in {
                    "english",
                    "conlang",
                    "compositional",
                    "contrastive",
                }
            },
            {
                "english": 3,
                "conlang": 3,
                "compositional": 3,
                "contrastive": 3,
            },
        )
        self.assertEqual(
            hashlib.sha256(QUERIES.read_bytes()).hexdigest(),
            MOTION_ACTION_EXPECTED_QUERY_SHA256,
        )

    def test_dry_plan_verifies_base_without_mutating_database_or_calling_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            db = self._copy_base(directory)
            report = directory / "absent-report.json"
            before_hash = hashlib.sha256(db.read_bytes()).hexdigest()
            before_mtime = db.stat().st_mtime_ns
            output = io.StringIO()
            with (
                patch("judeoalgonquin.cli.DEFAULT_STATIC_PLACE_DB", str(db)),
                patch(
                    "judeoalgonquin.cli.MOTION_ACTION_EMBEDDING_REPORT",
                    str(report),
                ),
                patch(
                    "judeoalgonquin.cli.OpenAIEmbedder",
                    side_effect=AssertionError("provider adapter constructed"),
                ),
                redirect_stdout(output),
            ):
                code = main(
                    [
                        "motion-action-embedding-eval",
                        "--data",
                        str(DATA),
                        "--queries",
                        str(QUERIES),
                        "--db",
                        str(db),
                        "--report",
                        str(report),
                    ]
                )
            result = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(result["mode"], "dry-run")
            self.assertEqual(result["base_fresh_record_vectors"], 180)
            self.assertEqual(result["incremental_records"], 45)
            self.assertEqual(result["full_evaluation_records"], 225)
            self.assertEqual(result["queries"], 12)
            self.assertEqual(result["api_inputs"], 57)
            self.assertEqual(result["api_requests"], 0)
            self.assertEqual(result["planned_provider_requests"], 1)
            self.assertEqual(result["provider_max_retries"], 0)
            self.assertEqual(result["dry_run_database_access"], "read-only")
            self.assertFalse(result["run_kind_currently_authorized"])
            self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before_hash)
            self.assertEqual(db.stat().st_mtime_ns, before_mtime)
            self.assertFalse(report.exists())

    def test_corrupted_base_vector_blob_is_rejected_by_frozen_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            db = self._copy_base(directory)
            report = directory / "absent-report.json"
            connection = sqlite3.connect(db)
            try:
                with connection:
                    connection.execute(
                        "UPDATE embeddings SET vector=zeroblob(length(vector)) "
                        "WHERE record_id=(SELECT min(record_id) FROM embeddings)"
                    )
            finally:
                connection.close()
            after_corruption = hashlib.sha256(db.read_bytes()).hexdigest()
            stderr = io.StringIO()
            with (
                patch("judeoalgonquin.cli.DEFAULT_STATIC_PLACE_DB", str(db)),
                patch(
                    "judeoalgonquin.cli.MOTION_ACTION_EMBEDDING_REPORT",
                    str(report),
                ),
                patch(
                    "judeoalgonquin.cli.OpenAIEmbedder",
                    side_effect=AssertionError("provider adapter constructed"),
                ),
                redirect_stderr(stderr),
            ):
                code = main(
                    [
                        "motion-action-embedding-eval",
                        "--data",
                        str(DATA),
                        "--queries",
                        str(QUERIES),
                        "--db",
                        str(db),
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("database content no longer matches", stderr.getvalue())
            self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), after_corruption)

    def test_live_flag_cannot_bypass_disabled_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            db = self._copy_base(directory)
            report = directory / "report.json"
            before_db = hashlib.sha256(db.read_bytes()).hexdigest()
            before_policy = hashlib.sha256(POLICY.read_bytes()).hexdigest()
            stderr = io.StringIO()
            with (
                patch("judeoalgonquin.cli.DEFAULT_STATIC_PLACE_DB", str(db)),
                patch(
                    "judeoalgonquin.cli.MOTION_ACTION_EMBEDDING_REPORT",
                    str(report),
                ),
                patch(
                    "judeoalgonquin.cli.OpenAIEmbedder",
                    side_effect=AssertionError("provider adapter constructed"),
                ),
                redirect_stderr(stderr),
            ):
                code = main(
                    [
                        "motion-action-embedding-eval",
                        "--data",
                        str(DATA),
                        "--queries",
                        str(QUERIES),
                        "--db",
                        str(db),
                        "--report",
                        str(report),
                        "--live",
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("explicit owner approval", stderr.getvalue())
            self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before_db)
            self.assertEqual(hashlib.sha256(POLICY.read_bytes()).hexdigest(), before_policy)
            self.assertFalse(report.exists())

    def test_authorized_path_uses_one_request_and_atomically_adds_only_45_vectors(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            db = self._copy_base(directory)
            report = directory / "report.json"
            connection = sqlite3.connect(db)
            try:
                base_vectors = dict(
                    connection.execute(
                        "SELECT record_id, vector FROM embeddings "
                        "WHERE model=? AND dimensions=?",
                        (DEFAULT_MODEL, DEFAULT_DIMENSIONS),
                    )
                )
            finally:
                connection.close()
            embedder = FakeOneShotEmbedder(
                model=DEFAULT_MODEL, dimensions=DEFAULT_DIMENSIONS
            )
            patches = self._live_patches(db, report, embedder)
            output = io.StringIO()
            with (
                patches[0],
                patches[1],
                patches[2] as reserve,
                patches[3] as complete,
                patches[4] as fail,
                patches[5],
                patch(
                    "judeoalgonquin.cli.evaluate_semantic_rankings",
                    wraps=real_evaluate_semantic_rankings,
                ) as evaluate,
                redirect_stdout(output),
            ):
                code = main(
                    [
                        "motion-action-embedding-eval",
                        "--data",
                        str(DATA),
                        "--queries",
                        str(QUERIES),
                        "--db",
                        str(db),
                        "--report",
                        str(report),
                        "--live",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(len(embedder.calls), 1)
            self.assertEqual(len(embedder.calls[0]), 57)
            reserve.assert_called_once()
            self.assertEqual(reserve.call_args.args[0], MOTION_ACTION_RUN_KIND)
            self.assertEqual(len(reserve.call_args.args[1]), 1)
            self.assertEqual(len(reserve.call_args.args[1][0]), 57)
            complete.assert_called_once()
            fail.assert_not_called()
            evaluate.assert_called_once()
            self.assertEqual(len(evaluate.call_args.args[0]), 225)
            self.assertEqual(len(evaluate.call_args.args[1]), 225)
            self.assertEqual(len(evaluate.call_args.args[2]), 12)
            self.assertEqual(len(evaluate.call_args.args[3]), 12)

            connection = sqlite3.connect(db)
            try:
                self.assertEqual(
                    connection.execute("SELECT count(*) FROM records").fetchone()[0],
                    225,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT count(*) FROM embeddings WHERE model=? AND dimensions=?",
                        (DEFAULT_MODEL, DEFAULT_DIMENSIONS),
                    ).fetchone()[0],
                    225,
                )
                after_vectors = dict(
                    connection.execute(
                        "SELECT record_id, vector FROM embeddings "
                        "WHERE model=? AND dimensions=?",
                        (DEFAULT_MODEL, DEFAULT_DIMENSIONS),
                    )
                )
            finally:
                connection.close()
            self.assertEqual(
                {record_id: after_vectors[record_id] for record_id in base_vectors},
                base_vectors,
            )
            self.assertEqual(len(set(after_vectors) - set(base_vectors)), 45)

            result = json.loads(output.getvalue())
            self.assertEqual(result["fresh_record_vectors"], 225)
            self.assertEqual(result["new_record_vectors"], 45)
            stored_report = json.loads(report.read_text(encoding="utf-8"))
            self.assertFalse(stored_report["contains_vectors"])
            self.assertFalse(stored_report["contains_credentials"])
            self.assertFalse(stored_report["contains_query_texts"])
            self.assertFalse(stored_report["contains_full_rankings"])
            self.assertEqual(stored_report["persisted_query_vectors"], 0)
            self.assertNotIn("query", stored_report["evaluation"]["diagnostics"][0])
            self.assertNotIn("ranking", stored_report["evaluation"]["diagnostics"][0])

            stored_report["unexpected_secret"] = "must-not-be-echoed"
            report.write_text(json.dumps(stored_report), encoding="utf-8")
            historical_output = io.StringIO()
            with (
                patch("judeoalgonquin.cli.DEFAULT_STATIC_PLACE_DB", str(db)),
                patch(
                    "judeoalgonquin.cli.MOTION_ACTION_EMBEDDING_REPORT",
                    str(report),
                ),
                redirect_stdout(historical_output),
            ):
                self.assertEqual(
                    main(
                        [
                            "motion-action-embedding-eval",
                            "--data",
                            str(DATA),
                            "--queries",
                            str(QUERIES),
                            "--db",
                            str(db),
                            "--report",
                            str(report),
                        ]
                    ),
                    0,
                )
            historical = json.loads(historical_output.getvalue())
            self.assertEqual(historical["mode"], "historical-report")
            self.assertNotIn(
                "unexpected_secret", historical["historical_checkpoint"]
            )
            self.assertNotIn(
                "diagnostics", historical["historical_checkpoint"]["evaluation"]
            )

    def test_staging_failure_leaves_original_database_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            db = self._copy_base(directory)
            report = directory / "report.json"
            before_hash = hashlib.sha256(db.read_bytes()).hexdigest()
            embedder = FakeOneShotEmbedder(
                model=DEFAULT_MODEL, dimensions=DEFAULT_DIMENSIONS
            )
            patches = self._live_patches(db, report, embedder)
            stderr = io.StringIO()
            with (
                patches[0],
                patches[1],
                patches[2],
                patches[3],
                patches[4],
                patches[5],
                patch(
                    "judeoalgonquin.cli.put_embeddings_atomic",
                    side_effect=RuntimeError("simulated atomic persistence failure"),
                ),
                redirect_stderr(stderr),
            ):
                code = main(
                    [
                        "motion-action-embedding-eval",
                        "--data",
                        str(DATA),
                        "--queries",
                        str(QUERIES),
                        "--db",
                        str(db),
                        "--report",
                        str(report),
                        "--live",
                    ]
                )
            self.assertEqual(code, 3)
            self.assertIn("live API action failed", stderr.getvalue())
            self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before_hash)
            self.assertFalse(report.exists())
            self.assertEqual(len(embedder.calls), 1)

    def test_report_write_failure_is_recoverable_without_a_second_provider_call(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            db = self._copy_base(directory)
            report = directory / "report.json"
            embedder = FakeOneShotEmbedder(
                model=DEFAULT_MODEL, dimensions=DEFAULT_DIMENSIONS
            )
            patches = self._live_patches(db, report, embedder)
            stderr = io.StringIO()
            with (
                patches[0],
                patches[1],
                patches[2],
                patches[3],
                patches[4],
                patches[5],
                patch(
                    "judeoalgonquin.cli._write_json_atomic",
                    side_effect=OSError("simulated report write failure"),
                ),
                redirect_stderr(stderr),
            ):
                code = main(
                    [
                        "motion-action-embedding-eval",
                        "--data",
                        str(DATA),
                        "--queries",
                        str(QUERIES),
                        "--db",
                        str(db),
                        "--report",
                        str(report),
                        "--live",
                    ]
                )
            self.assertEqual(code, 3)
            self.assertFalse(report.exists())
            connection = sqlite3.connect(db)
            try:
                self.assertEqual(
                    connection.execute("SELECT count(*) FROM records").fetchone()[0],
                    225,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT count(*) FROM embeddings WHERE model=? AND dimensions=?",
                        (DEFAULT_MODEL, DEFAULT_DIMENSIONS),
                    ).fetchone()[0],
                    225,
                )
            finally:
                connection.close()

            recovered_output = io.StringIO()
            with (
                patch("judeoalgonquin.cli.DEFAULT_STATIC_PLACE_DB", str(db)),
                patch(
                    "judeoalgonquin.cli.MOTION_ACTION_EMBEDDING_REPORT",
                    str(report),
                ),
                patch(
                    "judeoalgonquin.cli.OpenAIEmbedder",
                    side_effect=AssertionError("second provider call attempted"),
                ),
                redirect_stdout(recovered_output),
            ):
                recovered_code = main(
                    [
                        "motion-action-embedding-eval",
                        "--data",
                        str(DATA),
                        "--queries",
                        str(QUERIES),
                        "--db",
                        str(db),
                        "--report",
                        str(report),
                    ]
                )
            self.assertEqual(recovered_code, 0)
            self.assertTrue(report.exists())
            recovered = json.loads(recovered_output.getvalue())
            self.assertEqual(recovered["mode"], "historical-report")
            self.assertEqual(recovered["checkpoint_status"], "consumed")
            stored = json.loads(report.read_text(encoding="utf-8"))
            self.assertIn("report_recovered_at", stored)
            self.assertFalse(stored["contains_vectors"])
            self.assertFalse(stored["contains_credentials"])


if __name__ == "__main__":
    unittest.main()
