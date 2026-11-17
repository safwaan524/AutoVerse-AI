import re
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from database import (
    get_connection,
    execute_safe_query,
    search_vehicles,
    get_comparison_data,
    get_database_schema_info
)
from llm_engine import generate_response, chat_completion


GENERAL_KNOWLEDGE_KEYWORDS = [
    "difference between", "how does", "what is", "explain", "how do", 
    "pros and cons", "advantage", "disadvantage", "working principle",
    "turbocharger", "supercharger", "ev vs", "hybrid vs", "torque vs horsepower"
]


def classify_query_intent(query: str) -> str:
    """
    Classify user query into:
    - 'comparison': comparing two or more models
    - 'general_knowledge': automotive engineering / general conceptual questions
    - 'structured_query': database retrieval (prices, mileage, specs, counts)
    """
    q_lower = query.lower()

    if any(k in q_lower for k in ["compare", "vs", "versus", "difference between model"]):
        return "comparison"

    if any(k in q_lower for k in GENERAL_KNOWLEDGE_KEYWORDS) and not any(
        k in q_lower for k in ["price", "cost", "lakh", "under", "best mileage", "in stock", "used car", "list"]
    ):
        return "general_knowledge"

    return "structured_query"


def extract_sql_from_response(text: str) -> str:
    """Extract and sanitize raw SQL query from LLM text output."""
    # Match ```sql ... ``` or ``` ... ```
    match = re.search(r"```(?:sql)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        query = match.group(1).strip()
    else:
        query = text.strip()

    # Strip any leading 'SQL:' or trailing commentary
    query = re.sub(r"^(?:SQL|Query):\s*", "", query, flags=re.IGNORECASE).strip()
    # If multiple lines, only take the first SQL statement
    statements = query.split(";")
    sql = statements[0].strip()
    return sql


def sanitize_and_repair_sql(sql: str) -> str:
    """Repair common LLM SQL syntax misattributions."""
    repaired = sql
    # fuel_type_name is only on variants table (v)
    repaired = re.sub(r"\bp\.fuel_type_name\b", "v.fuel_type_name", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"\bp\.fuel_type\b", "v.fuel_type_name", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"\bm\.fuel_type_name\b", "v.fuel_type_name", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"\bm\.fuel_type\b", "v.fuel_type_name", repaired, flags=re.IGNORECASE)
    # mileage_kmpl is only on variants table (v)
    repaired = re.sub(r"\bp\.mileage_kmpl\b", "v.mileage_kmpl", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"\bm\.mileage_kmpl\b", "v.mileage_kmpl", repaired, flags=re.IGNORECASE)
    # engine_cc is only on variants table (v)
    repaired = re.sub(r"\bp\.engine_cc\b", "v.engine_cc", repaired, flags=re.IGNORECASE)
    # transmission_name is only on variants table (v)
    repaired = re.sub(r"\bp\.transmission_name\b", "v.transmission_name", repaired, flags=re.IGNORECASE)
    return repaired


def generate_sql_for_query(query: str) -> Optional[str]:
    """
    Use Llama 3 to convert natural language question into safe SQLite query.
    """
    schema = get_database_schema_info()
    prompt = f"""You are an expert SQLite query generator for an automotive intelligence database.
Generate ONLY a valid, read-only SQL query (SELECT statement) to answer the user question.

CRITICAL DATABASE SCHEMA RULES:
1. Output ONLY the raw SQL query. No explanation, markdown ticks, or preamble.
2. For questions about 'used car', 'pre-owned', or 'second hand' vehicles, query the 'used_listings' (u) table (e.g. SELECT AVG(price_inr) FROM used_listings WHERE price_inr > 0).
3. Join 'models' (m) with 'brands' (b) via: m.brand_slug = b.slug OR m.brand_source_id = b.source_id.
4. Join 'variants' (v) with 'models' (m) via: v.model_source_id = m.source_id.
5. Join 'prices' (p) with 'models' (m) and 'variants' (v) via: p.model_name = m.name AND p.variant_name = v.name.
6. In India: 1 Lakh = 100000 (10 Lakh = 1000000, 15 Lakh = 1500000).
7. Note: fuel_type_name, transmission_name, engine_cc, and mileage_kmpl exist ONLY in the 'variants' table (v). The 'prices' table (p) has ONLY ex_showroom_inr, on_road_inr, emi_inr, city_name.
8. Do NOT filter by m.status (it has nulls).
9. For price checks (e.g. under 10 lakh), use: (p.ex_showroom_inr <= 1000000 OR p.on_road_inr <= 1000000).
10. Use GROUP BY m.name, v.name when joining prices to avoid duplicate rows from different cities.
11. Always include relevant columns in SELECT: m.name AS model, b.name AS brand, v.name AS variant, v.fuel_type_name, v.mileage_kmpl, MIN(p.ex_showroom_inr) AS price.
12. Limit results using LIMIT 10 unless requesting an aggregate COUNT/AVG.

SCHEMA:
{schema}

USER QUESTION: {query}
SQL:"""

    raw_response = generate_response(prompt, temperature=0.1)
    sql = extract_sql_from_response(raw_response)
    if sql.upper().startswith("SELECT") or sql.upper().startswith("WITH"):
        return sanitize_and_repair_sql(sql)
    return None


def retrieve_rag_context(query: str) -> Dict[str, Any]:
    """
    Retrieve grounding context from the database using Natural-Language-to-SQL
    with hybrid keyword and parameter fallback.
    """
    intent = classify_query_intent(query)
    
    if intent == "general_knowledge":
        return {
            "intent": "general_knowledge",
            "context_text": "General automotive concept. No database query required.",
            "sql_query": None,
            "sql_columns": [],
            "sql_rows": [],
            "records_count": 0,
            "source": "automotive_domain_knowledge"
        }

    # Attempt NL-to-SQL
    sql = generate_sql_for_query(query)
    if sql:
        sql = sanitize_and_repair_sql(sql)
        cols, rows, err = execute_safe_query(sql, limit=15)
        
        # If error occurs, attempt auto-repair
        if err:
            fixed_sql = sanitize_and_repair_sql(sql)
            if fixed_sql != sql:
                cols, rows, err = execute_safe_query(fixed_sql, limit=15)
                if not err and rows:
                    sql = fixed_sql

        if not err and rows:
            # Format tabular context
            context_lines = [f"SQL Query Executed: {sql}", f"Columns: {', '.join(cols)}"]
            for idx, r in enumerate(rows[:10], 1):
                row_str = ", ".join([f"{c}: {val}" for c, val in zip(cols, r)])
                context_lines.append(f"Record {idx}: {row_str}")

            return {
                "intent": "structured_query",
                "context_text": "\n".join(context_lines),
                "sql_query": sql,
                "sql_columns": cols,
                "sql_rows": rows,
                "records_count": len(rows),
                "source": "database_sql"
            }

    # Fallback: Hybrid Attribute & Keyword Search
    q_lower = query.lower()
    fuel_filter = None
    if "diesel" in q_lower:
        fuel_filter = "Diesel"
    elif "petrol" in q_lower:
        fuel_filter = "Petrol"
    elif "cng" in q_lower:
        fuel_filter = "CNG"
    elif "electric" in q_lower or "ev" in q_lower:
        fuel_filter = "Electric"

    price_max = None
    if "10 lakh" in q_lower or "10l" in q_lower or "10 lakhs" in q_lower:
        price_max = 1000000
    elif "15 lakh" in q_lower or "15l" in q_lower:
        price_max = 1500000
    elif "20 lakh" in q_lower or "20l" in q_lower:
        price_max = 2000000
    elif "8 lakh" in q_lower:
        price_max = 800000
    elif "5 lakh" in q_lower:
        price_max = 500000

    df_search = search_vehicles(
        fuel_type=fuel_filter,
        max_price=price_max,
        query=None if fuel_filter or price_max else query,
        limit=8
    )

    if not df_search.empty:
        context_lines = [f"Retrieved {len(df_search)} matching vehicle records:"]
        for idx, row in df_search.iterrows():
            rec = (
                f"- {row.get('brand', '')} {row.get('model', '')} ({row.get('variant', '')}): "
                f"Fuel: {row.get('fuel_type', 'N/A')}, Transmission: {row.get('transmission', 'N/A')}, "
                f"Mileage: {row.get('mileage_kmpl', 'N/A')} kmpl, "
                f"Price: ₹{row.get('ex_showroom_inr', 0):,.0f}"
            )
            context_lines.append(rec)
        return {
            "intent": "keyword_search",
            "context_text": "\n".join(context_lines),
            "sql_query": sql,
            "sql_columns": list(df_search.columns),
            "sql_rows": [tuple(x) for x in df_search.values],
            "records_count": len(df_search),
            "source": "hybrid_search"
        }

    return {
        "intent": intent,
        "context_text": "No matching vehicle records found in the database.",
        "sql_query": sql,
        "sql_columns": [],
        "sql_rows": [],
        "records_count": 0,
        "source": "none"
    }


def answer_automotive_question(
    query: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Main RAG pipeline:
    1. Retrieve database context via NL-to-SQL or Keyword search.
    2. Build grounded prompt with strict anti-hallucination instructions.
    3. Query Ollama Llama 3.
    4. Return structured response with audit trail.
    """
    retrieval = retrieve_rag_context(query)
    context_text = retrieval["context_text"]
    intent = retrieval["intent"]

    system_prompt = """You are AutoVerse AI, an intelligent, authoritative automotive assistant.
You provide precise, insightful, and practical automotive advice.

STRICT GROUNDING RULES:
1. If database context is provided, ground your vehicle recommendations, prices, mileage, and specs strictly on those records.
2. NEVER invent, fabricate, or hallucinate vehicle prices, mileage numbers, or variants.
3. If specific vehicle data is not found in the context, explicitly state: "This information is not available in the AutoVerse database."
4. For general automotive engineering questions (e.g. how engines work, EV vs ICE), explain clearly and concisely using sound automotive engineering principles.
5. Format your response cleanly using bullet points, bold key specifications, and easy-to-read pricing formatted in Indian Lakhs/Rupees (₹)."""

    user_prompt = f"""DATABASE CONTEXT:
{context_text}

USER QUESTION:
{query}

Please answer the user's question clearly, adhering strictly to the grounding rules."""

    messages = []
    if conversation_history:
        # Include past turns (up to last 4)
        for msg in conversation_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_prompt})

    answer = chat_completion(
        messages=messages,
        system_prompt=system_prompt,
        temperature=0.2
    )

    return {
        "answer": answer,
        "context_text": context_text,
        "sql_query": retrieval.get("sql_query"),
        "sql_columns": retrieval.get("sql_columns", []),
        "sql_rows": retrieval.get("sql_rows", []),
        "records_count": retrieval.get("records_count", 0),
        "intent": intent,
        "source": retrieval.get("source")
    }


def ask_autoverse(question: str) -> str:
    """
    Backwards-compatible interface for existing scripts.
    Returns plain text response from AutoVerse AI.
    """
    result = answer_automotive_question(question)
    return result["answer"]


if __name__ == "__main__":
    test_q = "Which is the best diesel car under 10 lakh?"
    print(f"Testing RAG with question: '{test_q}'")
    out = answer_automotive_question(test_q)
    print("\n--- SQL QUERY ---")
    print(out["sql_query"])
    print("\n--- RECORDS FOUND ---", out["records_count"])
    print("\n--- AI ANSWER ---")
    print(out["answer"])
