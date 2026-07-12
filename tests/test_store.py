import copy
import tempfile
import unittest
from pathlib import Path

from judeoalgonquin.records import load_records, validate_records
from judeoalgonquin.store import (
    connect,
    count_fresh_embeddings,
    index_records,
    merge_hybrid_results,
    put_embedding,
    search_text,
    search_vectors,
)


FIXTURE = Path(__file__).parent / "fixtures" / "creative_anchor_candidates.jsonl"


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.connection = connect(Path(self.tempdir.name) / "test.sqlite3")
        self.addCleanup(self.connection.close)
        self.records = validate_records(load_records(FIXTURE))
        index_records(self.connection, self.records)

    def test_pointed_unpointed_romanized_and_english_search(self) -> None:
        expected = "ja.lexeme.legacy_home"
        for query in ("וִיגְוָאם", "ויגואם", "wigwaam", "house"):
            with self.subTest(query=query):
                results = search_text(self.connection, query)
                self.assertTrue(results)
                self.assertEqual(results[0]["id"], expected)
                self.assertEqual(results[0]["lexical_score"], 100.0)

    def test_deprecated_is_hidden_by_default(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["status"] = "deprecated"
        records[0]["review"] = {
            "reviewer_type": "human",
            "reviewer_id": "test-reviewer",
            "authority": "unit test",
            "decision": "deprecated",
            "reviewed_at": "2026-07-12T00:00:00Z",
            "note": "test",
        }
        validate_records(records)
        index_records(self.connection, records)
        default_results = search_text(self.connection, "wigwaam")
        self.assertNotIn(
            "ja.lexeme.legacy_home", {result["id"] for result in default_results}
        )
        self.assertEqual(
            search_text(self.connection, "wigwaam", statuses=("deprecated",))[0]["id"],
            "ja.lexeme.legacy_home",
        )

    def test_reindex_removes_absent_record(self) -> None:
        index_records(self.connection, self.records[:2])
        count = self.connection.execute("SELECT count(*) FROM records").fetchone()[0]
        self.assertEqual(count, 2)

    def test_vector_search_and_hybrid_exact_priority(self) -> None:
        from judeoalgonquin.embeddings import record_fingerprint

        model = "fake"
        vectors = {
            "ja.lexeme.legacy_home": [1.0, 0.0, 0.0],
            "ja.phrase.legacy_in_the_home": [0.9, 0.1, 0.0],
            "ja.lexeme.legacy_path": [0.0, 1.0, 0.0],
        }
        records_by_id = {record["id"]: record for record in self.records}
        for record_id, vector in vectors.items():
            put_embedding(
                self.connection,
                record_id,
                model,
                3,
                record_fingerprint(records_by_id[record_id], model, 3),
                vector,
            )
        semantic = search_vectors(
            self.connection, [1.0, 0.0, 0.0], model=model, dimensions=3
        )
        self.assertEqual(semantic[0]["id"], "ja.lexeme.legacy_home")
        lexical = search_text(self.connection, "path")
        hybrid = merge_hybrid_results(lexical, semantic, limit=3)
        self.assertEqual(hybrid[0]["id"], "ja.lexeme.legacy_path")

    def test_changed_record_stale_vector_is_not_searchable(self) -> None:
        from judeoalgonquin.embeddings import record_fingerprint

        record = self.records[0]
        put_embedding(
            self.connection,
            record["id"],
            "fake",
            3,
            record_fingerprint(record, "fake", 3),
            [1.0, 0.0, 0.0],
        )
        self.assertEqual(
            search_vectors(
                self.connection, [1.0, 0.0, 0.0], model="fake", dimensions=3
            )[0]["id"],
            record["id"],
        )

        changed = copy.deepcopy(self.records)
        changed[0]["revision"] = 2
        changed[0]["notes"]["design"].append("A material revision invalidates the vector.")
        index_records(self.connection, changed)
        result_ids = {
            item["id"]
            for item in search_vectors(
                self.connection, [1.0, 0.0, 0.0], model="fake", dimensions=3
            )
        }
        self.assertNotIn(record["id"], result_ids)
        self.assertEqual(
            count_fresh_embeddings(
                self.connection, model="fake", dimensions=3, statuses=("candidate",)
            ),
            0,
        )

    def test_changed_dependency_hides_downstream_vector(self) -> None:
        from judeoalgonquin.embeddings import record_fingerprint

        phrase = self.records[1]
        put_embedding(
            self.connection,
            phrase["id"],
            "fake",
            3,
            record_fingerprint(phrase, "fake", 3),
            [1.0, 0.0, 0.0],
        )
        self.assertEqual(
            search_vectors(
                self.connection, [1.0, 0.0, 0.0], model="fake", dimensions=3
            )[0]["id"],
            phrase["id"],
        )

        changed = copy.deepcopy(self.records)
        changed[0]["revision"] = 2
        index_records(self.connection, changed)
        downstream_ids = {
            item["id"]
            for item in search_vectors(
                self.connection, [1.0, 0.0, 0.0], model="fake", dimensions=3
            )
        }
        self.assertNotIn(phrase["id"], downstream_ids)


if __name__ == "__main__":
    unittest.main()
