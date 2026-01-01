from bike_agent.agent.llm_client import call_llm

def test_hf_llm():
    response = call_llm({
        "system_prompt": "You are a helpful assistant. Reply with valid JSON only.",
        "user_message": {
            "type": "PING"
        }
    })

    print("LLM OUTPUT:")
    print(response)

if __name__ == "__main__":
    test_hf_llm()
