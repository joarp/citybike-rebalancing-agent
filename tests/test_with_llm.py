import sys
import os
import json
from dotenv import load_dotenv
import requests

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL")

if not MISTRAL_API_KEY or not MISTRAL_API_URL:
    raise ValueError("MISTRAL_API_KEY or MISTRAL_API_URL not set in .env")

# -------------------------------
# Import orchestrator
# -------------------------------
from bike_agent.agent import orchestrator as orch_module

# -------------------------------
# Real LLM function
# -------------------------------
def real_llm(input_data):
    system_prompt = input_data["system_prompt"]
    user_message = input_data["user_message"]

    prompt = f"{system_prompt}\n\nUSER INPUT:\n{json.dumps(user_message)}"

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-7b",
        "prompt": prompt,
        "max_tokens": 1024,
        "temperature": 0.2
    }

    response = requests.post(MISTRAL_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()

    # Adjust according to Mistral API
    output_text = result.get("output_text") or result.get("choices", [{}])[0].get("text")
    if not output_text:
        raise ValueError(f"No output_text found in Mistral response: {result}")

    return output_text

# -------------------------------
# Test orchestrator with real LLM
# -------------------------------
def test_orchestrator_with_llm():
    task_payload = {
        "start": {"lat": 39.566056, "lon": 2.659389},
        "truck_capacity": 10,
        "time_budget_min": 120,
        "context": {}
    }

    # Monkey patch orchestrator to use real LLM
    orch_module.call_llm = real_llm

    # Run orchestrator
    context = orch_module.orchestrator(task_payload)
    print("\n===== FINAL CONTEXT =====")
    print(json.dumps(context, indent=2))

# -------------------------------
# Run test
# -------------------------------
if __name__ == "__main__":
    test_orchestrator_with_llm()
