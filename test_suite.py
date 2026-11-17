import unittest
import pandas as pd
from config import DATABASE_PATH, FORBIDDEN_SQL_KEYWORDS
import database
import llm_engine
import rag_engine
import recommendations
import comparison
import analytics


class TestAutoVerseAI(unittest.TestCase):

    def test_01_database_stats(self):
        """Verify database exists and tables contain records."""
        stats = database.get_database_stats()
        self.assertGreater(stats.get("brands", 0), 0)
        self.assertGreater(stats.get("models", 0), 0)
        self.assertGreater(stats.get("variants", 0), 0)
        self.assertGreater(stats.get("prices", 0), 0)
        self.assertGreater(stats.get("used_listings", 0), 0)

    def test_02_sql_read_only_safety(self):
        """Verify SQL safety validator strictly blocks forbidden DDL/DML."""
        cols, rows, err = database.execute_safe_query("DROP TABLE brands")
        self.assertIsNotNone(err)
        self.assertIn("Access Denied", err)

        cols, rows, err = database.execute_safe_query("DELETE FROM models")
        self.assertIsNotNone(err)

        cols, rows, err = database.execute_safe_query("SELECT COUNT(*) FROM brands")
        self.assertIsNone(err)
        self.assertEqual(len(rows), 1)

    def test_03_vehicle_search(self):
        """Verify vehicle search works with filters."""
        res = database.search_vehicles(brand="Tata", fuel_type="Diesel", limit=5)
        self.assertFalse(res.empty)
        self.assertIn("brand", res.columns)
        self.assertIn("model", res.columns)

    def test_04_vehicle_comparison_data(self):
        """Verify comparison data retrieval for multiple models."""
        comp = database.get_comparison_data(["Creta", "Seltos"])
        self.assertFalse(comp.empty)
        self.assertEqual(len(comp), 2)

    def test_05_recommendation_candidates(self):
        """Verify recommendation engine retrieves valid candidates within budget."""
        candidates = database.get_recommendation_candidates(
            budget=1200000,
            fuel_preference="Petrol",
            seats=5,
            limit=4
        )
        self.assertFalse(candidates.empty)
        self.assertLessEqual(len(candidates), 4)

    def test_06_analytics_data(self):
        """Verify analytics queries produce non-empty datasets."""
        data = database.get_analytics_data()
        self.assertIn("brand_prices", data)
        self.assertIn("used_stats", data)
        self.assertFalse(data["brand_prices"].empty)
        self.assertFalse(data["used_stats"].empty)

    def test_07_ollama_status(self):
        """Verify Ollama connection and llama3 model availability."""
        is_online, models, err = llm_engine.check_ollama_status()
        self.assertTrue(is_online, f"Ollama should be online. Error: {err}")
        self.assertTrue(any("llama3" in m for m in models), "llama3 should be present in Ollama models")

    def test_08_rag_engine_grounding(self):
        """Verify RAG engine returns grounded response with audit metadata."""
        out = rag_engine.answer_automotive_question("Which cars offer the best mileage?")
        self.assertIsNotNone(out.get("answer"))
        self.assertGreater(len(out.get("answer")), 20)
        self.assertIn(out.get("intent"), ["structured_query", "keyword_search"])


if __name__ == "__main__":
    unittest.main()
