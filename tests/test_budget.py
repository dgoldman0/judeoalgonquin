import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import judeoalgonquin.budget as budget_module
from judeoalgonquin.budget import (
    budget_snapshot,
    complete_paid_embedding_run,
    load_policy,
    reserve_paid_embedding_checkpoint,
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
                    "authorization_id": "unit-test-authorization",
                    "authorization_consumed": False,
                    "allowed_run_kinds": ["test"],
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
            value = json.loads(policy.read_text(encoding="utf-8"))
            value["authorization_id"] = "unit-test-second-authorization"
            value["authorization_consumed"] = False
            policy.write_text(json.dumps(value), encoding="utf-8")
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

    def test_scoped_checkpoint_kind_and_authorization_are_one_shot(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            policy = self._policy(directory, enabled=True)
            value = json.loads(policy.read_text(encoding="utf-8"))
            value.update(
                {
                    "allowed_run_kinds": ["frozen-checkpoint"],
                    "authorization_id": "one-shot-test",
                    "authorization_consumed": False,
                    "max_provider_requests_per_checkpoint": 2,
                    "max_input_utf8_bytes": 100,
                }
            )
            policy.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "kind"):
                reserve_paid_embedding_checkpoint(
                    "generic-search",
                    [["hello"]],
                    model="fake-model",
                    dimensions=3,
                    policy_path=policy,
                )
            reservation = reserve_paid_embedding_checkpoint(
                "frozen-checkpoint",
                [["hello"], ["again"]],
                model="fake-model",
                dimensions=3,
                policy_path=policy,
            )
            self.assertEqual(reservation.authorization_id, "one-shot-test")
            persisted = json.loads(policy.read_text(encoding="utf-8"))
            self.assertTrue(persisted["authorization_consumed"])
            (directory / "ledger.json").unlink()
            with self.assertRaisesRegex(ValueError, "already consumed"):
                reserve_paid_embedding_checkpoint(
                    "frozen-checkpoint",
                    [["third"]],
                    model="fake-model",
                    dimensions=3,
                    policy_path=policy,
                )

    def test_enabled_policy_requires_complete_one_shot_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            policy = self._policy(directory, enabled=True)
            complete = json.loads(policy.read_text(encoding="utf-8"))
            for missing in (
                "authorization_id",
                "authorization_consumed",
                "allowed_run_kinds",
            ):
                with self.subTest(missing=missing):
                    candidate = {**complete}
                    candidate.pop(missing)
                    policy.write_text(json.dumps(candidate), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "scoped authorization"):
                        load_policy(policy)

    def test_scoped_reservation_consumes_policy_before_ledger_write(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            policy = self._policy(directory, enabled=True)
            value = json.loads(policy.read_text(encoding="utf-8"))
            value.update(
                {
                    "allowed_run_kinds": ["frozen-checkpoint"],
                    "authorization_id": "fail-closed-test",
                    "authorization_consumed": False,
                }
            )
            policy.write_text(json.dumps(value), encoding="utf-8")
            real_write = budget_module._write_json_atomic

            def fail_ledger_write(path, payload):
                if path == directory / "ledger.json":
                    raise OSError("simulated ledger write failure")
                real_write(path, payload)

            with (
                patch(
                    "judeoalgonquin.budget._write_json_atomic",
                    side_effect=fail_ledger_write,
                ),
                self.assertRaisesRegex(OSError, "simulated"),
            ):
                reserve_paid_embedding_checkpoint(
                    "frozen-checkpoint",
                    [["hello"]],
                    model="fake-model",
                    dimensions=3,
                    policy_path=policy,
                )
            persisted = json.loads(policy.read_text(encoding="utf-8"))
            self.assertTrue(persisted["authorization_consumed"])
            self.assertFalse((directory / "ledger.json").exists())

    def test_committed_baseline_survives_a_fresh_authorization_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            policy = self._policy(directory, enabled=False, total_cap=700_000)
            value = json.loads(policy.read_text(encoding="utf-8"))
            value["historical_accounted_input_tokens"] = 694_040
            value["ledger_path"] = str(directory / "fresh-ledger.json")
            policy.write_text(json.dumps(value), encoding="utf-8")
            snapshot = budget_snapshot(policy)
            self.assertEqual(snapshot["cumulative_accounted_input_tokens"], 694_040)
            self.assertEqual(snapshot["authorization_ledger_accounted_input_tokens"], 0)
            self.assertEqual(snapshot["remaining_authorized_input_tokens"], 5_960)

    def test_nonpositive_and_nonfinite_prices_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            policy = self._policy(directory, enabled=True)
            original = json.loads(policy.read_text(encoding="utf-8"))
            for key, value in (
                ("price_per_million_input_tokens_usd", -0.02),
                ("price_per_million_input_tokens_usd", math.nan),
                ("max_estimated_cost_usd", math.inf),
            ):
                with self.subTest(key=key, value=value):
                    candidate = {**original, key: value}
                    policy.write_text(json.dumps(candidate), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "model, dimensions, or cost"):
                        load_policy(policy)

    def test_negative_ledger_totals_and_reservation_overrun_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            policy = self._policy(directory, enabled=True)
            ledger_path = directory / "ledger.json"
            ledger_path.write_text(
                json.dumps(
                    {
                        "accounted_input_tokens": -1,
                        "completed_input_tokens": 0,
                        "runs": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "malformed"):
                reserve_paid_embedding_run(
                    "test", ["hello"], model="fake-model", dimensions=3, policy_path=policy
                )

            ledger_path.write_text(
                json.dumps(
                    {
                        "accounted_input_tokens": 1,
                        "completed_input_tokens": 0,
                        "runs": [
                            {
                                "status": "failed_or_unknown",
                                "reserved_token_upper_bound": 5,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "totals do not match"):
                budget_snapshot(policy)

            ledger_path.unlink()
            reservation = reserve_paid_embedding_run(
                "test", ["hello"], model="fake-model", dimensions=3, policy_path=policy
            )
            with self.assertRaisesRegex(ValueError, "integrity"):
                complete_paid_embedding_run(
                    reservation, reservation.reserved_token_upper_bound + 1
                )


if __name__ == "__main__":
    unittest.main()
