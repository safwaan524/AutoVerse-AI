
import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key or api_key == "your_api_key_here":
    print("ERROR: Gemini API key not configured.")
else:
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Introduce yourself as the AI assistant of AutoVerse AI."
        )

        print("\nAUTOVERSE AI RESPONSE:")
        print(response.text)

    except Exception as e:
        print("Gemini connection error:", e)
