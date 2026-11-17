from typing import List, Dict, Any, Optional
from rag_engine import answer_automotive_question
from llm_engine import check_ollama_status


def handle_user_message(
    user_message: str,
    conversation_history: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Process a user chat message through RAG pipeline with conversation memory.
    Returns structured result with answer, context, SQL, and status.
    """
    is_online, models, err = check_ollama_status()
    if not is_online:
        return {
            "answer": (
                "⚠️ **Ollama Service Unavailable**\n\n"
                f"Cannot connect to the local Ollama LLM server at `http://localhost:11434`.\n\n"
                "**To resolve this:**\n"
                "1. Open Terminal and start Ollama: `ollama serve`\n"
                "2. Ensure Llama 3 is installed: `ollama pull llama3`\n"
                "3. Refresh the page once Ollama is running."
            ),
            "sql_query": None,
            "records_count": 0,
            "source": "offline_error",
            "is_error": True
        }

    # Run RAG engine
    rag_result = answer_automotive_question(
        query=user_message,
        conversation_history=conversation_history
    )
    rag_result["is_error"] = False
    return rag_result


STARTER_PROMPTS = [
    "Which is the best diesel car under ₹10 lakh?",
    "Compare Hyundai Creta and Kia Seltos in detail.",
    "Which cars offer the best mileage in India?",
    "What is the average price of used cars?",
    "Explain the difference between petrol and diesel engines.",
    "Recommend a 7-seater family car under ₹15 lakh."
]
