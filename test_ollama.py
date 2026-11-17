
import requests
import json

url = "http://localhost:11434/api/chat"

payload = {
    "model": "llama3",
    "messages": [
        {
            "role": "user",
            "content": "Explain how a car engine works in simple words."
        }
    ],
    "stream": False
}

try:
    response = requests.post(url, json=payload)
    response.raise_for_status()

    result = response.json()

    print("\n===== AUTOVERSE AI =====\n")
    print(result["message"]["content"])

    print("\n===== CONNECTION SUCCESSFUL =====")

except Exception as e:
    print("Connection error:", e)
