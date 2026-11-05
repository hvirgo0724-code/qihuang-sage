import unittest
from unittest.mock import Mock, patch

from app.core import llm


class EmbeddingTests(unittest.TestCase):
    def test_batch_boundaries_and_order(self):
        for count in (1, 10, 11, 25):
            with self.subTest(count=count):
                client = Mock()
                client.embed_documents.side_effect = lambda batch: [[float(t)] for t in batch]
                texts = [str(i) for i in range(count)]
                with patch.object(llm, "embeddings_client", return_value=client):
                    result = llm.embed_texts(texts)
                self.assertEqual([v[0] for v in result], list(range(count)))
                batches = [call.args[0] for call in client.embed_documents.call_args_list]
                self.assertTrue(all(1 <= len(batch) <= 10 for batch in batches))
                self.assertEqual([t for batch in batches for t in batch], texts)
                self.assertEqual(len(batches), (count + 9) // 10)

    def test_empty_input_does_not_create_client(self):
        with patch.object(llm, "embeddings_client") as factory:
            self.assertEqual(llm.embed_texts([]), [])
            factory.assert_not_called()

    def test_incomplete_response_is_rejected(self):
        client = Mock()
        client.embed_documents.return_value = [[1.0]]
        with patch.object(llm, "embeddings_client", return_value=client):
            with self.assertRaisesRegex(ValueError, "count"):
                llm.embed_texts(["a", "b"])

    def test_failed_batch_stops_remaining_requests(self):
        client = Mock()
        client.embed_documents.side_effect = [ [[1.0]] * 10, RuntimeError("rate limited") ]
        with patch.object(llm, "embeddings_client", return_value=client):
            with self.assertRaisesRegex(RuntimeError, "rate limited"):
                llm.embed_texts(["text"] * 25)
        self.assertEqual(client.embed_documents.call_count, 2)
