# bike_agent/agent/llm_client.py
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env (local dev only)
load_dotenv()

# Read API key (works for both .env and GitHub Secrets)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Choose your OpenAI model
MODEL_NAME = "gpt-4o-mini"


def call_llm(input_data):
    """
    input_data: dict with keys:
      - "system_prompt": str
      - "user_message": dict or str
    """

    system_prompt = input_data.get("system_prompt", "")
    user_message = input_data.get("user_message", {})

    # Serialize user message safely
    if isinstance(user_message, dict):
        user_content = json.dumps(user_message, ensure_ascii=False)
    else:
        user_content = str(user_message)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=512,
    )

    return response.choices[0].message.content
