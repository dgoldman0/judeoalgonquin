"""Persistent paid-API authorization and token accounting."""

from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

import fcntl


DEFAULT_POLICY_PATH = Path("config/api-budget.json")


@dataclass(frozen=True)
class Reservation:
    run_id: str
    ledger_path: Path
    reserved_token_upper_bound: int


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


@contextmanager
def _ledger_lock(path: Path) -> Iterator[None]:
    """Serialize each ledger read-modify-write cycle across local processes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    with lock_path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_policy(path: str | Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    path = Path(path)
    policy = _read_json(path, {})
    required = {
        "paid_embeddings_enabled": bool,
        "authorization_note": str,
        "allowed_models": list,
        "allowed_dimensions": list,
        "max_inputs_per_run": int,
        "max_utf8_bytes_per_run": int,
        "max_total_input_tokens": int,
        "max_estimated_cost_usd": (int, float),
        "price_per_million_input_tokens_usd": (int, float),
        "ledger_path": str,
    }
    for key, expected_type in required.items():
        if key not in policy or not isinstance(policy[key], expected_type):
            raise ValueError(f"{path}: invalid or missing {key}")
    if any(
        policy[key] < 1
        for key in ("max_inputs_per_run", "max_utf8_bytes_per_run", "max_total_input_tokens")
    ):
        raise ValueError(f"{path}: budget caps must be positive")
    if (
        not policy["allowed_models"]
        or any(not isinstance(model, str) or not model for model in policy["allowed_models"])
        or not policy["allowed_dimensions"]
        or any(
            not isinstance(dimensions, int)
            or isinstance(dimensions, bool)
            or dimensions < 1
            for dimensions in policy["allowed_dimensions"]
        )
        or policy["max_estimated_cost_usd"] <= 0
    ):
        raise ValueError(f"{path}: invalid model, dimensions, or cost authorization")
    return policy


def token_upper_bound(texts: Sequence[str]) -> int:
    """UTF-8 bytes are a conservative upper bound for text-token count."""

    return sum(len(text.encode("utf-8")) for text in texts)


def reserve_paid_embedding_run(
    kind: str,
    texts: Sequence[str],
    *,
    model: str,
    dimensions: int,
    policy_path: str | Path = DEFAULT_POLICY_PATH,
) -> Reservation:
    policy = load_policy(policy_path)
    if not policy["paid_embeddings_enabled"]:
        raise ValueError(
            "paid embeddings are disabled by config/api-budget.json; explicit owner approval is required"
        )
    if model not in policy["allowed_models"]:
        raise ValueError(f"embedding model {model!r} is outside the authorized policy")
    if dimensions not in policy["allowed_dimensions"]:
        raise ValueError(
            f"embedding dimensions {dimensions} are outside the authorized policy"
        )
    if not texts or len(texts) > policy["max_inputs_per_run"]:
        raise ValueError("planned input count exceeds the authorized per-run cap")
    byte_count = sum(len(text.encode("utf-8")) for text in texts)
    if byte_count > policy["max_utf8_bytes_per_run"]:
        raise ValueError("planned input bytes exceed the authorized per-run cap")
    reserve_tokens = token_upper_bound(texts)
    ledger_path = Path(policy["ledger_path"])
    run_id = uuid.uuid4().hex
    with _ledger_lock(ledger_path):
        ledger = _read_json(
            ledger_path,
            {"accounted_input_tokens": 0, "completed_input_tokens": 0, "runs": []},
        )
        accounted = ledger.get("accounted_input_tokens")
        runs = ledger.get("runs")
        if not isinstance(accounted, int) or not isinstance(runs, list):
            raise ValueError(f"{ledger_path}: malformed paid-API ledger")
        if accounted + reserve_tokens > policy["max_total_input_tokens"]:
            raise ValueError("planned run exceeds the authorized cumulative input-token cap")
        estimated_cost = (
            (accounted + reserve_tokens)
            * policy["price_per_million_input_tokens_usd"]
            / 1_000_000
        )
        if estimated_cost > policy["max_estimated_cost_usd"]:
            raise ValueError("planned run exceeds the authorized cumulative dollar cap")
        ledger["accounted_input_tokens"] = accounted + reserve_tokens
        runs.append(
            {
                "run_id": run_id,
                "kind": kind,
                "model": model,
                "dimensions": dimensions,
                "status": "reserved",
                "reserved_token_upper_bound": reserve_tokens,
                "input_count": len(texts),
                "reserved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _write_json_atomic(ledger_path, ledger)
    return Reservation(run_id, ledger_path, reserve_tokens)


def complete_paid_embedding_run(reservation: Reservation, actual_input_tokens: int) -> None:
    if actual_input_tokens < 0:
        raise ValueError("actual token usage cannot be negative")
    with _ledger_lock(reservation.ledger_path):
        ledger = _read_json(reservation.ledger_path, {})
        runs = ledger.get("runs")
        if not isinstance(runs, list):
            raise ValueError(f"{reservation.ledger_path}: malformed paid-API ledger")
        run = next((item for item in runs if item.get("run_id") == reservation.run_id), None)
        if run is None or run.get("status") != "reserved":
            raise ValueError("paid-API reservation is missing or already finalized")
        accounted = ledger.get("accounted_input_tokens")
        completed = ledger.get("completed_input_tokens")
        if not isinstance(accounted, int) or not isinstance(completed, int):
            raise ValueError(f"{reservation.ledger_path}: malformed paid-API totals")
        ledger["accounted_input_tokens"] = (
            accounted - reservation.reserved_token_upper_bound + actual_input_tokens
        )
        ledger["completed_input_tokens"] = completed + actual_input_tokens
        run.update(
            {
                "status": "completed",
                "actual_input_tokens": actual_input_tokens,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _write_json_atomic(reservation.ledger_path, ledger)


def fail_paid_embedding_run(reservation: Reservation, error_type: str) -> None:
    """Keep the conservative reservation counted when billing outcome is uncertain."""

    with _ledger_lock(reservation.ledger_path):
        ledger = _read_json(reservation.ledger_path, {})
        runs = ledger.get("runs")
        if not isinstance(runs, list):
            return
        run = next((item for item in runs if item.get("run_id") == reservation.run_id), None)
        if run is None or run.get("status") != "reserved":
            return
        run.update(
            {
                "status": "failed_or_unknown",
                "error_type": error_type,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _write_json_atomic(reservation.ledger_path, ledger)
