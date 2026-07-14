import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from judeoalgonquin.cli import main


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "creative_anchor_candidates.jsonl"
PILOT = ROOT / "data" / "entries" / "n1-pilot.jsonl"
STATIC_REPORT = (
    ROOT / "docs" / "reports" / "static-place-semantic-bootstrap-2026-07-13.json"
)


class CliTests(unittest.TestCase):
    def test_smoke_defaults_to_no_api_dry_run(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["smoke", "--fixture", str(FIXTURE)])
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["api_requests"], 0)
        self.assertEqual(result["api_inputs"], 4)

    def test_build_and_lexical_search_are_local(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            db = str(Path(tempdir) / "kb.sqlite3")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(["build", "--data", str(FIXTURE), "--db", db]), 0
                )
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["search", "home", "--db", db]), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["mode"], "lexical")
            self.assertEqual(result["results"][0]["id"], "ja.lexeme.legacy_home")

    def test_consumed_live_smoke_is_refused_before_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(
                    [
                        "smoke",
                        "--fixture",
                        str(FIXTURE),
                        "--db",
                        str(Path(tempdir) / "smoke.sqlite3"),
                        "--live",
                    ]
                )
        self.assertEqual(code, 2)
        self.assertIn("already recorded", stderr.getvalue())

    def test_live_smoke_without_report_still_requires_budget_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            stderr = io.StringIO()
            missing_report = str(Path(tempdir) / "missing-smoke-report.json")
            with (
                patch("judeoalgonquin.cli.SMOKE_REPORT", missing_report),
                patch(
                    "judeoalgonquin.cli.OpenAIEmbedder",
                    side_effect=AssertionError("provider adapter constructed"),
                ),
                redirect_stderr(stderr),
            ):
                code = main(
                    [
                        "smoke",
                        "--fixture",
                        str(FIXTURE),
                        "--db",
                        str(Path(tempdir) / "smoke.sqlite3"),
                        "--live",
                    ]
                )
        self.assertEqual(code, 2)
        self.assertIn("explicit owner approval", stderr.getvalue())

    def test_bulk_live_embedding_is_disabled_by_committed_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(
                    [
                        "embed",
                        "--data",
                        str(FIXTURE),
                        "--db",
                        str(Path(tempdir) / "kb.sqlite3"),
                        "--limit",
                        "1",
                        "--live",
                    ]
                )
        self.assertEqual(code, 2)
        self.assertIn("explicit owner approval", stderr.getvalue())

    def test_pilot_composition_evaluation_is_local(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["evaluate", "--data", str(PILOT)]), 0)
        result = json.loads(output.getvalue())
        self.assertTrue(result["valid"])
        self.assertEqual(result["records"], 20)
        self.assertEqual(result["construction_findings"], [])

    def test_pilot_embedding_evaluation_defaults_to_one_request_dry_run(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["pilot-embedding-eval"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["evaluation_kind"], "retrieval_sanity_test")
        self.assertEqual(result["api_requests"], 0)
        self.assertEqual(result["api_inputs"], 25)
        self.assertLess(result["conservative_cost_upper_bound_usd"], 0.002)

    def test_n1_core_embedding_evaluation_plans_current_tree_without_request(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["n1-core-embedding-eval"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["records"], 264)
        self.assertEqual(result["queries"], 12)
        self.assertEqual(result["api_inputs"], 276)
        self.assertEqual(result["api_requests"], 0)
        self.assertLess(result["conservative_cost_upper_bound_usd"], 0.015)

    def test_static_place_bootstrap_reports_consumed_historical_checkpoint(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["static-place-embedding-eval"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["mode"], "historical-report")
        self.assertEqual(result["checkpoint_status"], "consumed")
        self.assertEqual(result["api_requests"], 0)
        self.assertEqual(result["current_records"], 264)
        historical = result["historical_checkpoint"]
        self.assertEqual(historical["mode"], "live")
        self.assertEqual(historical["records"], 180)
        self.assertEqual(historical["queries"], 16)
        self.assertEqual(historical["api_inputs"], 196)
        self.assertEqual(historical["logical_provider_batches"], 2)
        self.assertFalse(historical["http_attempts_instrumented"])
        self.assertEqual(historical["sdk_default_max_retries_at_run"], 2)
        self.assertTrue(historical["evaluation"]["passed"])
        self.assertNotIn("queries", historical["evaluation"])
        self.assertNotIn("record_revisions", historical)

    def test_static_place_live_rerun_is_refused_as_consumed(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["static-place-embedding-eval", "--live"])
        self.assertEqual(code, 2)
        self.assertIn("authorization is already consumed", stderr.getvalue())

    def test_historical_checkpoint_output_whitelists_safe_summary_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            report_path = Path(tempdir) / "historical.json"
            report = json.loads(STATIC_REPORT.read_text(encoding="utf-8"))
            report["unexpected_secret"] = "must-not-be-echoed"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            output = io.StringIO()
            with (
                patch(
                    "judeoalgonquin.cli.STATIC_PLACE_EMBEDDING_REPORT",
                    str(report_path),
                ),
                redirect_stdout(output),
            ):
                self.assertEqual(main(["static-place-embedding-eval"]), 0)
        result = json.loads(output.getvalue())
        self.assertNotIn("unexpected_secret", result["historical_checkpoint"])
        self.assertNotIn("ranking", output.getvalue())



if __name__ == "__main__":
    unittest.main()
