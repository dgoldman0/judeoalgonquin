import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from judeoalgonquin.cli import main


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "creative_anchor_candidates.jsonl"
PILOT = ROOT / "data" / "entries" / "n1-pilot.jsonl"


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
        self.assertEqual(result["records"], 144)
        self.assertEqual(result["queries"], 12)
        self.assertEqual(result["api_inputs"], 156)
        self.assertEqual(result["api_requests"], 0)
        self.assertLess(result["conservative_cost_upper_bound_usd"], 0.008)



if __name__ == "__main__":
    unittest.main()
