import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from neo4j.time import Date, DateTime, Duration, Time

from app.api import knowledge
from app.services import knowledge_service as service


class KnowledgeDetailTests(unittest.TestCase):
    def test_temporal_properties_serialize_through_all_detail_routes(self):
        app = FastAPI()
        app.include_router(knowledge.router)
        app.dependency_overrides[knowledge.get_current_user] = lambda: object()
        app.dependency_overrides[knowledge.get_db] = lambda: None
        stamp = DateTime(2026, 11, 4, 8, 30, 0)

        def query(cypher, params):
            props = {"name": params["name"], "updated_at": stamp,
                     "nested": [Date(2026, 11, 4), Time(8, 30, 0), Duration(days=1)]}
            if "labels(m)" in cypher:
                return [{"props": props, "labels": ["Herb"]}]
            return [{"props": props}]

        with patch.object(service, "_graph_available", return_value=True), \
                patch.object(service.neo4j_client, "run_query", side_effect=query), \
                TestClient(app) as client:
            for route in ("formulas", "herbs", "syndromes", "symptoms"):
                with self.subTest(route=route):
                    response = client.get(f"/knowledge/{route}/测试节点")
                    self.assertEqual(response.status_code, 200, response.text)
                    detail = response.json()
                    self.assertEqual(detail["node"]["properties"]["updated_at"], stamp.iso_format())
                    self.assertEqual(detail["node"]["properties"]["nested"][0], "2026-11-04")
                    self.assertTrue(detail["neighbors"])
                    for neighbor in detail["neighbors"]:
                        self.assertEqual(neighbor["related"]["properties"]["updated_at"], stamp.iso_format())


if __name__ == "__main__":
    unittest.main()
