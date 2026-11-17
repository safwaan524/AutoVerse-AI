import unittest
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

import api_server


client = TestClient(api_server.app)


class TestAutoVerseAPI(unittest.TestCase):
    @patch("api_server.llm_engine.check_ollama_status", return_value=(False, [], "offline"))
    @patch("api_server.database.get_database_stats", return_value={"models": 2})
    def test_health(self, mock_stats, mock_ollama):
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["data"]["status"], "degraded")

    @patch(
        "api_server.database.search_vehicles",
        return_value=pd.DataFrame([{"brand": "Tata", "model": "Nexon"}]),
    )
    def test_vehicle_search(self, mock_search):
        response = client.get("/api/vehicles", params={"brand": "Tata", "limit": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["count"], 1)
        mock_search.assert_called_once()

    @patch(
        "api_server.database.get_vehicle_details",
        return_value={
            "model": {"model_name": "Nexon"},
            "variants": pd.DataFrame(
                [{"variant_name": "Smart", "key_features": b"\x00\xff"}]
            ),
        },
    )
    def test_vehicle_details(self, mock_details):
        response = client.get("/api/vehicles/Nexon")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["variants"][0]["variant_name"], "Smart"
        )
        self.assertEqual(
            response.json()["data"]["variants"][0]["key_features"],
            {"encoding": "base64", "data": "AP8="},
        )

    @patch("api_server.comparison.generate_ai_vehicle_comparison", return_value="Analysis")
    @patch(
        "api_server.database.get_comparison_data",
        return_value=pd.DataFrame([{"model_name": "Creta"}, {"model_name": "Seltos"}]),
    )
    @patch("api_server.database.get_models_by_brand", return_value=["Creta", "Seltos"])
    def test_compare(self, mock_models, mock_specs, mock_analysis):
        response = client.post(
            "/api/compare", json={"model_names": ["Creta", "Seltos"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["analysis"], "Analysis")

    @patch(
        "api_server.recommendations.get_ai_recommendations",
        return_value={
            "candidates": pd.DataFrame([{"model": "Nexon"}]),
            "total_matches": 1,
            "ai_rationale": "Fits the requested criteria.",
        },
    )
    def test_recommendations(self, mock_recommendations):
        response = client.post("/api/recommendations", json={"budget": 1200000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["total_matches"], 1)

    @patch(
        "api_server.database.get_analytics_data",
        return_value={"brand_prices": pd.DataFrame([{"brand": "Tata"}])},
    )
    def test_analytics(self, mock_analytics):
        response = client.get("/api/analytics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["brand_prices"][0]["brand"], "Tata"
        )

    @patch(
        "api_server.chatbot.handle_user_message",
        return_value={"answer": "Hello", "is_error": False},
    )
    def test_chat_accepts_client_history(self, mock_chat):
        response = client.post(
            "/api/chat",
            json={
                "message": "Hello",
                "conversation_history": [
                    {"role": "user", "content": f"old {index}"}
                    for index in range(5)
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["answer"], "Hello")
        self.assertEqual(len(mock_chat.call_args.args[1]), 4)

    def test_rejects_invalid_vehicle_price_range(self):
        response = client.get(
            "/api/vehicles", params={"min_price": 5000, "max_price": 1000}
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["success"])


if __name__ == "__main__":
    unittest.main()
