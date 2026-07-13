"""Persistent paid-API authorization and token accounting."""

from __future__ import annotations

import json
import math
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
    lock_path: Path
    reserved_token_upper_bound: int
    authorization_id: str


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


def _authorization_lock_path(policy_path: Path) -> Path:
    """Return a stable per-policy lock without dirtying the tracked config tree."""

    if policy_path.resolve() == DEFAULT_POLICY_PATH.resolve():
        return Path(".local/api-budget-policy")
    return policy_path.with_name(f".{policy_path.name}.authorization")


def _validated_ledger(
    ledger: dict[str, Any], ledger_path: Path
) -> tuple[int, int, list[dict[str, Any]]]:
    """Validate totals against every stored run, not merely their JSON types."""

    accounted = ledger.get("accounted_input_tokens")
    completed = ledger.get("completed_input_tokens")
    runs = ledger.get("runs")
    if (
        not isinstance(accounted, int)
        or isinstance(accounted, bool)
        or not isinstance(completed, int)
        or isinstance(completed, bool)
        or accounted < 0
        or completed < 0
        or completed > accounted
        or not isinstance(runs, list)
        or any(not isinstance(run, dict) for run in runs)
    ):
        raise ValueError(f"{ledger_path}: malformed paid-API ledger")

    computed_accounted = 0
    computed_completed = 0
    for run in runs:
        status = run.get("status")
        reserved = run.get("reserved_token_upper_bound")
        if (
            not isinstance(reserved, int)
            or isinstance(reserved, bool)
            or reserved < 0
        ):
            raise ValueError(f"{ledger_path}: malformed paid-API run reservation")
        if status in {"reserved", "failed_or_unknown"}:
            computed_accounted += reserved
        elif status == "completed":
            actual = run.get("actual_input_tokens")
            if (
                not isinstance(actual, int)
                or isinstance(actual, bool)
                or actual < 0
                or actual > reserved
            ):
                raise ValueError(f"{ledger_path}: malformed completed paid-API run")
            computed_accounted += actual
            computed_completed += actual
        else:
            raise ValueError(f"{ledger_path}: unknown paid-API run status")
    if accounted != computed_accounted or completed != computed_completed:
        raise ValueError(f"{ledger_path}: paid-API ledger totals do not match its runs")
    return accounted, completed, runs


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
    integer_caps = (
        "max_inputs_per_run",
        "max_utf8_bytes_per_run",
        "max_total_input_tokens",
    )
    if any(isinstance(policy[key], bool) for key in integer_caps):
        raise ValueError(f"{path}: budget caps must be positive integers")
    if any(
        policy[key] < 1
        for key in integer_caps
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
        or isinstance(policy["max_estimated_cost_usd"], bool)
        or isinstance(policy["price_per_million_input_tokens_usd"], bool)
        or not math.isfinite(float(policy["max_estimated_cost_usd"]))
        or not math.isfinite(float(policy["price_per_million_input_tokens_usd"]))
        or policy["max_estimated_cost_usd"] <= 0
        or policy["price_per_million_input_tokens_usd"] <= 0
    ):
        raise ValueError(f"{path}: invalid model, dimensions, or cost authorization")
    optional_types = {
        "allowed_run_kinds": list,
        "authorization_id": str,
        "authorization_consumed": bool,
        "historical_accounted_input_tokens": int,
        "max_provider_requests_per_checkpoint": int,
        "max_input_utf8_bytes": int,
    }
    for key, expected_type in optional_types.items():
        if key in policy and not isinstance(policy[key], expected_type):
            raise ValueError(f"{path}: invalid {key}")
    for key in (
        "historical_accounted_input_tokens",
        "max_provider_requests_per_checkpoint",
        "max_input_utf8_bytes",
    ):
        if key in policy and isinstance(policy[key], bool):
            raise ValueError(f"{path}: invalid {key}")
    if any(
        policy.get(key, 1) < 1
        for key in ("max_provider_requests_per_checkpoint", "max_input_utf8_bytes")
    ) or policy.get("historical_accounted_input_tokens", 0) < 0:
        raise ValueError(f"{path}: invalid checkpoint or historical budget cap")
    allowed_kinds = policy.get("allowed_run_kinds", [])
    if any(not isinstance(kind, str) or not kind for kind in allowed_kinds):
        raise ValueError(f"{path}: invalid allowed_run_kinds")
    if policy["paid_embeddings_enabled"] and (
        not policy.get("authorization_id")
        or "authorization_consumed" not in policy
        or not allowed_kinds
    ):
        raise ValueError(
            f"{path}: enabled paid access requires a scoped authorization id, "
            "an explicit consumed marker, and allowed run kinds"
        )
    return policy


def token_upper_bound(texts: Sequence[str]) -> int:
    """UTF-8 bytes are a conservative upper bound for text-token count."""

    return sum(len(text.encode("utf-8")) for text in texts)


def budget_snapshot(
    policy_path: str | Path = DEFAULT_POLICY_PATH,
) -> dict[str, int | float]:
    """Return sanitized cumulative accounting for a dry-run plan."""

    policy = load_policy(policy_path)
    ledger_path = Path(policy["ledger_path"])
    ledger = _read_json(
        ledger_path,
        {"accounted_input_tokens": 0, "completed_input_tokens": 0, "runs": []},
    )
    accounted, completed, _ = _validated_ledger(ledger, ledger_path)
    historical = int(policy.get("historical_accounted_input_tokens", 0))
    cumulative = historical + accounted
    price = float(policy["price_per_million_input_tokens_usd"])
    return {
        "historical_accounted_input_tokens": historical,
        "authorization_ledger_accounted_input_tokens": accounted,
        "authorization_ledger_completed_input_tokens": completed,
        "cumulative_accounted_input_tokens": cumulative,
        "remaining_authorized_input_tokens": int(policy["max_total_input_tokens"])
        - cumulative,
        "cumulative_accounted_cost_usd": cumulative * price / 1_000_000,
        "remaining_authorized_cost_usd": float(policy["max_estimated_cost_usd"])
        - cumulative * price / 1_000_000,
    }


def reserve_paid_embedding_run(
    kind: str,
    texts: Sequence[str],
    *,
    model: str,
    dimensions: int,
    policy_path: str | Path = DEFAULT_POLICY_PATH,
) -> Reservation:
    return reserve_paid_embedding_checkpoint(
        kind,
        [texts],
        model=model,
        dimensions=dimensions,
        policy_path=policy_path,
    )


def reserve_paid_embedding_checkpoint(
    kind: str,
    batches: Sequence[Sequence[str]],
    *,
    model: str,
    dimensions: int,
    policy_path: str | Path = DEFAULT_POLICY_PATH,
) -> Reservation:
    """Reserve one logical checkpoint containing bounded provider batches.

    The authorization is consumed at reservation time.  A later network failure
    therefore cannot turn into a quiet retry or an unaccounted second attempt.
    """

    policy_path = Path(policy_path)
    run_id = uuid.uuid4().hex
    lock_path = _authorization_lock_path(policy_path)
    with _ledger_lock(lock_path):
        policy = load_policy(policy_path)
        if not policy["paid_embeddings_enabled"]:
            raise ValueError(
                "paid embeddings are disabled by config/api-budget.json; "
                "explicit owner approval is required"
            )
        allowed_kinds = policy.get("allowed_run_kinds", [])
        if allowed_kinds and kind not in allowed_kinds:
            raise ValueError(
                f"paid embedding kind {kind!r} is outside the authorized policy"
            )
        authorization_id = policy["authorization_id"]
        if policy.get("authorization_consumed", False):
            raise ValueError(
                f"paid embedding authorization {authorization_id!r} is already consumed"
            )
        if model not in policy["allowed_models"]:
            raise ValueError(
                f"embedding model {model!r} is outside the authorized policy"
            )
        if dimensions not in policy["allowed_dimensions"]:
            raise ValueError(
                f"embedding dimensions {dimensions} are outside the authorized policy"
            )
        if (
            not batches
            or len(batches) > policy.get("max_provider_requests_per_checkpoint", 1)
            or any(not batch for batch in batches)
        ):
            raise ValueError(
                "planned provider request count exceeds the authorized checkpoint cap"
            )
        texts = [text for batch in batches for text in batch]
        max_input_bytes = policy.get(
            "max_input_utf8_bytes", policy["max_utf8_bytes_per_run"]
        )
        for batch in batches:
            if len(batch) > policy["max_inputs_per_run"]:
                raise ValueError(
                    "planned input count exceeds the authorized per-provider-request cap"
                )
            batch_bytes = token_upper_bound(batch)
            if batch_bytes > policy["max_utf8_bytes_per_run"]:
                raise ValueError(
                    "planned input bytes exceed the authorized per-provider-request cap"
                )
            if any(len(text.encode("utf-8")) > max_input_bytes for text in batch):
                raise ValueError(
                    "an embedding input exceeds the authorized per-input byte cap"
                )
        reserve_tokens = token_upper_bound(texts)
        ledger_path = Path(policy["ledger_path"])
        ledger = _read_json(
            ledger_path,
            {"accounted_input_tokens": 0, "completed_input_tokens": 0, "runs": []},
        )
        accounted, _, runs = _validated_ledger(ledger, ledger_path)
        if any(
            run.get("authorization_id") == authorization_id for run in runs
        ):
            raise ValueError(
                f"paid embedding authorization {authorization_id!r} is already consumed"
            )
        historical = policy.get("historical_accounted_input_tokens", 0)
        if historical + accounted + reserve_tokens > policy["max_total_input_tokens"]:
            raise ValueError("planned run exceeds the authorized cumulative input-token cap")
        estimated_cost = (
            (historical + accounted + reserve_tokens)
            * policy["price_per_million_input_tokens_usd"]
            / 1_000_000
        )
        if estimated_cost > policy["max_estimated_cost_usd"]:
            raise ValueError("planned run exceeds the authorized cumulative dollar cap")
        ledger["accounted_input_tokens"] = accounted + reserve_tokens
        runs.append(
            {
                "run_id": run_id,
                "authorization_id": authorization_id,
                "kind": kind,
                "model": model,
                "dimensions": dimensions,
                "status": "reserved",
                "reserved_token_upper_bound": reserve_tokens,
                "input_count": len(texts),
                "provider_requests": len(batches),
                "provider_batches": [
                    {
                        "input_count": len(batch),
                        "utf8_bytes": token_upper_bound(batch),
                    }
                    for batch in batches
                ],
                "reserved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        # Fail closed: a crash after this write can lose an authorization,
        # but it cannot leave an apparently reusable one after reservation.
        policy["authorization_consumed"] = True
        _write_json_atomic(policy_path, policy)
        _write_json_atomic(ledger_path, ledger)
    return Reservation(
        run_id,
        ledger_path,
        lock_path,
        reserve_tokens,
        authorization_id,
    )


def complete_paid_embedding_run(reservation: Reservation, actual_input_tokens: int) -> None:
    if (
        not isinstance(actual_input_tokens, int)
        or isinstance(actual_input_tokens, bool)
        or actual_input_tokens < 0
    ):
        raise ValueError("actual token usage must be a nonnegative integer")
    with _ledger_lock(reservation.lock_path):
        ledger = _read_json(reservation.ledger_path, {})
        accounted, completed, runs = _validated_ledger(
            ledger, reservation.ledger_path
        )
        run = next((item for item in runs if item.get("run_id") == reservation.run_id), None)
        if run is None or run.get("status") != "reserved":
            raise ValueError("paid-API reservation is missing or already finalized")
        stored_reservation = run.get("reserved_token_upper_bound")
        if (
            run.get("authorization_id") != reservation.authorization_id
            or not isinstance(stored_reservation, int)
            or isinstance(stored_reservation, bool)
            or stored_reservation < 0
            or reservation.reserved_token_upper_bound != stored_reservation
            or actual_input_tokens > stored_reservation
        ):
            raise ValueError("paid-API reservation integrity check failed")
        if accounted < stored_reservation:
            raise ValueError(f"{reservation.ledger_path}: malformed paid-API totals")
        ledger["accounted_input_tokens"] = (
            accounted - stored_reservation + actual_input_tokens
        )
        ledger["completed_input_tokens"] = completed + actual_input_tokens
        run.update(
            {
                "status": "completed",
                "actual_input_tokens": actual_input_tokens,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _validated_ledger(ledger, reservation.ledger_path)
        _write_json_atomic(reservation.ledger_path, ledger)


def fail_paid_embedding_run(reservation: Reservation, error_type: str) -> None:
    """Keep the conservative reservation counted when billing outcome is uncertain."""

    with _ledger_lock(reservation.lock_path):
        ledger = _read_json(reservation.ledger_path, {})
        _, _, runs = _validated_ledger(ledger, reservation.ledger_path)
        run = next((item for item in runs if item.get("run_id") == reservation.run_id), None)
        if run is None or run.get("status") != "reserved":
            return
        if (
            run.get("authorization_id") != reservation.authorization_id
            or run.get("reserved_token_upper_bound")
            != reservation.reserved_token_upper_bound
        ):
            raise ValueError("paid-API reservation integrity check failed")
        run.update(
            {
                "status": "failed_or_unknown",
                "error_type": error_type,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _validated_ledger(ledger, reservation.ledger_path)
        _write_json_atomic(reservation.ledger_path, ledger)
