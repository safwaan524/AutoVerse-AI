import requests
import json
from typing import List, Dict, Any, Tuple, Optional, Generator
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


def check_ollama_status() -> Tuple[bool, List[str], Optional[str]]:
    """
    Check if the local Ollama server is running and which models are installed.
    Returns: (is_online, model_names, error_message)
    """
    url = f"{OLLAMA_BASE_URL}/api/tags"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, models, None
        return False, [], f"Ollama returned HTTP {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, [], f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. Ensure 'ollama serve' is running."


def generate_response(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.2,
    model: str = OLLAMA_MODEL
) -> str:
    """
    Generate a completion using Ollama. Backwards compatible with original llm_engine.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    if system:
        payload["system"] = system

    try:
        response = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()
    except requests.exceptions.Timeout:
        return "Error: Ollama request timed out. Please verify the model is loaded."
    except requests.exceptions.RequestException as e:
        return f"Ollama connection error: {e}. Please ensure Ollama is running on localhost:11434."


def chat_completion(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    stream: bool = False,
    temperature: float = 0.2,
    model: str = OLLAMA_MODEL
) -> Any:
    """
    Chat completion endpoint supporting multi-turn conversation history.
    If stream=True, returns a generator yielding chunks of text.
    If stream=False, returns the complete response string.
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"

    # Prepend system prompt if provided
    formatted_messages = []
    if system_prompt:
        formatted_messages.append({"role": "system", "content": system_prompt})
    formatted_messages.extend(messages)

    payload = {
        "model": model,
        "messages": formatted_messages,
        "stream": stream,
        "options": {
            "temperature": temperature
        }
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=OLLAMA_TIMEOUT,
            stream=stream
        )
        response.raise_for_status()

        if stream:
            def stream_generator() -> Generator[str, None, None]:
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                            msg = chunk.get("message", {}).get("content", "")
                            if msg:
                                yield msg
                        except json.JSONDecodeError:
                            continue
            return stream_generator()
        else:
            data = response.json()
            return data.get("message", {}).get("content", "").strip()

    except requests.exceptions.Timeout:
        err_msg = "Error: Ollama request timed out. The model may be processing a heavy load."
        return (chunk for chunk in [err_msg]) if stream else err_msg
    except requests.exceptions.RequestException as e:
        err_msg = f"Ollama connection error: {e}. Please ensure Ollama is running on localhost:11434."
        return (chunk for chunk in [err_msg]) if stream else err_msg


if __name__ == "__main__":
    print("Testing llm_engine.py...")
    status, models, err = check_ollama_status()
    print("Ollama Status:", status, "Models:", models, "Error:", err)
    if status:
        res = generate_response("What is horsepower in a car? Answer in one short sentence.")
        print("Test response:", res)
