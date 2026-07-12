import json
import tempfile
import unittest
from pathlib import Path

from judeoalgonquin.budget import (
    complete_paid_embedding_run,
    reserve_paid_embedding_run,
)


class BudgetTests(unittest.TestCase):
    def _policy(self, directory: Path, *, enabled: bool, total_cap: int = 1000) -> Path:
        path = directory / "policy.json"
        path.write_text(
            json.dumps(
                {
                    "paid_embeddings_enabled": enabled,
                    "authorization_note": "unit test",
                    "allowed_models": ["fake-model"],
                    "allowed_dimensions": [3],
                    "max_inputs_per_run": 2,
                    "max_utf8_bytes_per_run": 100,
                    "max_total_input_tokens": total_cap,
                    "max_estimated_cost_usd": 1.0,
                    "price_per_million_input_tokens_usd": 0.02,
                    "ledger_path": str(directory / "ledger.json"),
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_disabled_policy_blocks_before_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            policy = self._policy(Path(tempdir), enabled=False)
            with self.assertRaisesRegex(ValueError, "disabled"):
                reserve_paid_embedding_run(
                    "test", ["hello"], model="fake-model", dimensions=3, policy_path=policy
                )

    def test_reservation_and_actual_usage_are_persistent(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            policy = self._policy(directory, enabled=True)
            reservation = reserve_paid_embedding_run(
                "test", ["hello"], model="fake-model", dimensions=3, policy_path=policy
            )
            ledger = json.loads((directory / "ledger.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["runs"][0]["status"], "reserved")
            self.assertGreater(ledger["accounted_input_tokens"], 0)
            complete_paid_embedding_run(reservation, 2)
            ledger = json.loads((directory / "ledger.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["accounted_input_tokens"], 2)
            self.assertEqual(ledger["completed_input_tokens"], 2)
            self.assertEqual(ledger["runs"][0]["status"], "completed")

    def test_cumulative_cap_counts_reservations(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            policy = self._policy(directory, enabled=True, total_cap=6)
            reserve_paid_embedding_run(
                "test", ["hello"], model="fake-model", dimensions=3, policy_path=policy
            )
            with self.assertRaisesRegex(ValueError, "cumulative"):
                reserve_paid_embedding_run(
                    "test", ["again"], model="fake-model", dimensions=3, policy_path=policy
                )

    def test_model_and_dimensions_are_locked_by_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            policy = self._policy(Path(tempdir), enabled=True)
            with self.assertRaisesRegex(ValueError, "model"):
                reserve_paid_embedding_run(
                    "test", ["hello"], model="other", dimensions=3, policy_path=policy
                )
            with self.assertRaisesRegex(ValueError, "dimensions"):
                reserve_paid_embedding_run(
                    "test", ["hello"], model="fake-model", dimensions=99, policy_path=policy
                )


if __name__ == "__main__":
    unittest.main()
