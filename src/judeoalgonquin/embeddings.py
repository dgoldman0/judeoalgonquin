"""Cost-gated OpenAI embeddings and deterministic record projections."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from .records import canonical_json
from .store import embedding_fingerprint, put_embedding


DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIMENSIONS = 256
# The provider currently accepts much larger arrays, but an N1 epoch is locally
# constrained to one inspectable batch. Individual commands may impose a smaller
# consumed-checkpoint envelope.
MAX_LIVE_INPUTS = 128


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    prompt_tokens: int
    total_tokens: int


class Embedder(Protocol):
    model: str
    dimensions: int

    def embed(self, texts: Sequence[str]) -> EmbeddingBatch: ...


def embedding_text(record: dict[str, Any]) -> str:
    forms = record["forms"]
    conlang = forms["judeo_algonquin"]
    notes = record["notes"]
    lines = [
        f"record type: {record['record_type']}",
        f"project level: {record['level']}",
        "English: " + " | ".join(forms["english"]),
        "Judeo-Algonquin: " + conlang["hebrew_script"],
        "Romanization: " + conlang["romanization"],
        "Orthography: " + canonical_json(conlang["orthography"]),
    ]
    for sense in record["senses"]:
        lines.append(
            "sense: "
            + " | ".join(sense["glosses"])
            + f"; {sense['definition']}; part of speech: {sense['part_of_speech']}"
        )
        translations = sense["translations"]
        if translations["literal"]:
            lines.append("literal translation: " + " | ".join(translations["literal"]))
        lines.append("idiomatic translation: " + " | ".join(translations["idiomatic"]))
    if record["grammatical_features"]:
        lines.append("grammatical features: " + " | ".join(record["grammatical_features"]))
    for label, values in (
        ("translation notes", notes["translation"]),
        ("grammar notes", notes["grammar"]),
        ("design notes", notes["design"]),
    ):
        if values:
            lines.append(f"{label}: " + " | ".join(values))
    formation = record["formation"]
    lines.append("formation kind: " + formation["formation_kind"])
    for formation_input in formation["inputs"]:
        lines.append(
            "formation input: "
            + formation_input["input_type"]
            + " "
            + formation_input["input_id"]
            + "; form: "
            + (formation_input["form"] or "not applicable")
            + "; contribution: "
            + formation_input["contribution"]
        )
    for operation in formation["operations"]:
        lines.append(
            f"formation operation {operation['order']}: {operation['operation']}; "
            + operation["description"]
        )
    if formation["formation_process"]:
        lines.append("formation process: " + formation["formation_process"])
    if formation["design_alignment"]:
        lines.append("design alignment: " + formation["design_alignment"])
    for evidence in record["source_evidence"]:
        lect = f" ({evidence['lect']})" if evidence["lect"] else ""
        lines.append(
            f"source evidence: {evidence['language']}{lect}: {evidence['source_form']} — "
            f"{evidence['source_meaning']}; grammatical information: "
            f"{evidence['grammatical_information'] or 'not supplied by source'}; "
            f"confidence: {evidence['confidence']}; uncertainty: "
            f"{evidence['uncertainty'] or 'none recorded'}; contributor or speaker: "
            f"{evidence['contributor_or_speaker'] or 'not published'}; use: "
            f"{evidence['use_type']}; supports: {' | '.join(evidence['supports_sense_ids'])}"
        )
    if record["composition"]:
        lines.append("composition: " + canonical_json(record["composition"]))
    if record["construction_spec"]:
        lines.append("construction specification: " + canonical_json(record["construction_spec"]))
    if record["paradigm"]:
        lines.append("paradigm: " + canonical_json(record["paradigm"]))
    if record.get("narrative_analysis"):
        lines.append(
            "narrative analysis: "
            + canonical_json(record["narrative_analysis"])
        )
    return "\n".join(lines)


def fingerprint(text: str, model: str, dimensions: int) -> str:
    payload = f"{model}\0{dimensions}\0{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def record_fingerprint(record: dict[str, Any], model: str, dimensions: int) -> str:
    # Canonical JSON is included so metadata/provenance revisions invalidate stale vectors.
    payload = embedding_text(record) + "\nrecord-json-sha256: " + hashlib.sha256(
        canonical_json(record).encode("utf-8")
    ).hexdigest()
    return fingerprint(payload, model, dimensions)


class OpenAIEmbedder:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        dimensions: int = DEFAULT_DIMENSIONS,
        client: Any | None = None,
    ) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        self.model = model
        self.dimensions = dimensions
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "The optional OpenAI SDK is required for a live call. "
                    "Install openai>=2.15,<3 in the active environment."
                ) from exc
            # Paid checkpoints are explicitly bounded and owner-authorized.
            # Provider retries must therefore be a new visible authorization,
            # never an SDK-default replay after an ambiguous response.
            client = OpenAI(max_retries=0)
        self.client = client

    def embed(self, texts: Sequence[str]) -> EmbeddingBatch:
        if not texts:
            raise ValueError("at least one embedding input is required")
        if len(texts) > MAX_LIVE_INPUTS:
            raise ValueError(f"live input cap is {MAX_LIVE_INPUTS}")
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("embedding inputs must be non-empty strings")
        response = self.client.embeddings.create(
            model=self.model,
            input=list(texts),
            dimensions=self.dimensions,
            encoding_format="float",
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = [list(item.embedding) for item in ordered]
        if len(vectors) != len(texts):
            raise RuntimeError("embedding API returned an unexpected number of vectors")
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise RuntimeError("embedding API returned unexpected dimensions")
        usage = response.usage
        return EmbeddingBatch(
            vectors=vectors,
            prompt_tokens=int(usage.prompt_tokens),
            total_tokens=int(usage.total_tokens),
        )


def records_needing_embeddings(
    connection: Any,
    records: Sequence[dict[str, Any]],
    *,
    model: str,
    dimensions: int,
) -> list[dict[str, Any]]:
    needed: list[dict[str, Any]] = []
    revisions = {
        record["id"]: record["revision"]
        for record in records
        if isinstance(record.get("id"), str) and isinstance(record.get("revision"), int)
    }
    for record in records:
        expected_dependencies = record.get("relations", {}).get("dependency_revisions", {})
        if not isinstance(expected_dependencies, dict) or any(
            revisions.get(dependency_id) != dependency_revision
            for dependency_id, dependency_revision in expected_dependencies.items()
        ):
            raise ValueError(
                f"{record.get('id', '<unknown>')}: dependency revisions are stale or missing"
            )
        expected = record_fingerprint(record, model, dimensions)
        actual = embedding_fingerprint(connection, record["id"], model, dimensions)
        if actual != expected:
            needed.append(record)
    return needed


def embed_records(
    connection: Any,
    records: Sequence[dict[str, Any]],
    embedder: Embedder,
    *,
    limit: int,
) -> tuple[int, EmbeddingBatch | None]:
    if limit < 1 or limit > MAX_LIVE_INPUTS:
        raise ValueError(f"limit must be between 1 and {MAX_LIVE_INPUTS}")
    needed = records_needing_embeddings(
        connection, records, model=embedder.model, dimensions=embedder.dimensions
    )
    selected = needed[:limit]
    if not selected:
        return 0, None
    batch = embedder.embed([embedding_text(record) for record in selected])
    for record, vector in zip(selected, batch.vectors):
        put_embedding(
            connection,
            record["id"],
            embedder.model,
            embedder.dimensions,
            record_fingerprint(record, embedder.model, embedder.dimensions),
            vector,
        )
    return len(selected), batch
