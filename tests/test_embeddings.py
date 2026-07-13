import copy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from judeoalgonquin.embeddings import (
    EmbeddingBatch,
    OpenAIEmbedder,
    embed_records,
    embedding_text,
    record_fingerprint,
    records_needing_embeddings,
)
from judeoalgonquin.records import load_records, validate_records
from judeoalgonquin.store import connect, index_records


FIXTURE = Path(__file__).parent / "fixtures" / "creative_anchor_candidates.jsonl"


class FakeEmbedder:
    model = "fake-model"
    dimensions = 3

    def __init__(self) -> None:
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        vectors = []
        for text in texts:
            lowered = text.casefold()
            if "house" in lowered or "home" in lowered:
                vectors.append([1.0, 0.0, 0.0])
            elif "path" in lowered or "road" in lowered:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return EmbeddingBatch(vectors=vectors, prompt_tokens=len(texts), total_tokens=len(texts))


class EmbeddingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = validate_records(load_records(FIXTURE))
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.connection = connect(Path(self.tempdir.name) / "test.sqlite3")
        self.addCleanup(self.connection.close)
        index_records(self.connection, self.records)

    def test_projection_is_deterministic_and_explanatory(self) -> None:
        first = embedding_text(self.records[0])
        second = embedding_text(copy.deepcopy(self.records[0]))
        self.assertEqual(first, second)
        self.assertIn("English: house | home | dwelling", first)
        self.assertIn("design alignment", first)

    def test_record_revision_changes_fingerprint(self) -> None:
        changed = copy.deepcopy(self.records[0])
        changed["revision"] += 1
        self.assertNotEqual(
            record_fingerprint(self.records[0], "fake", 3),
            record_fingerprint(changed, "fake", 3),
        )

    def test_incremental_cache_avoids_second_call(self) -> None:
        embedder = FakeEmbedder()
        count, batch = embed_records(self.connection, self.records, embedder, limit=3)
        self.assertEqual(count, 3)
        self.assertIsNotNone(batch)
        self.assertEqual(embedder.calls, 1)
        self.assertEqual(
            records_needing_embeddings(
                self.connection,
                self.records,
                model=embedder.model,
                dimensions=embedder.dimensions,
            ),
            [],
        )
        count, batch = embed_records(self.connection, self.records, embedder, limit=3)
        self.assertEqual((count, batch), (0, None))
        self.assertEqual(embedder.calls, 1)

    def test_openai_adapter_batches_and_checks_dimensions(self) -> None:
        response = SimpleNamespace(
            data=[SimpleNamespace(index=0, embedding=[0.0, 1.0, 0.0])],
            usage=SimpleNamespace(prompt_tokens=4, total_tokens=4),
        )
        client = SimpleNamespace(
            embeddings=SimpleNamespace(create=lambda **kwargs: response)
        )
        embedder = OpenAIEmbedder(model="fake", dimensions=3, client=client)
        batch = embedder.embed(["test"])
        self.assertEqual(batch.vectors, [[0.0, 1.0, 0.0]])
        self.assertEqual(batch.total_tokens, 4)

    def test_default_openai_client_disables_automatic_retries(self) -> None:
        captured = {}

        def factory(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(embeddings=SimpleNamespace(create=None))

        fake_module = SimpleNamespace(OpenAI=factory)
        with patch.dict(sys.modules, {"openai": fake_module}):
            OpenAIEmbedder(model="fake", dimensions=3)
        self.assertEqual(captured, {"max_retries": 0})

    def test_live_input_cap_is_enforced_before_provider(self) -> None:
        client = SimpleNamespace(
            embeddings=SimpleNamespace(create=lambda **kwargs: self.fail("provider called"))
        )
        embedder = OpenAIEmbedder(model="fake", dimensions=3, client=client)
        with self.assertRaisesRegex(ValueError, "cap"):
            embedder.embed(["x"] * 129)


if __name__ == "__main__":
    unittest.main()
