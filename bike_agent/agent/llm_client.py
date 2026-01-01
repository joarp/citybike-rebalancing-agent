# bike_agent/agent/llm_client.py
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
import json

# Choose your model
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"

print("Loading model, this can take a few minutes...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",        # auto assigns GPU if available
    torch_dtype=torch.bfloat16 # use fp16 or bf16 for GPU efficiency
)
llm_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)

def call_llm(input_data):
    """
    input_data: dict with "system_prompt" and "user_message"
    """
    system_prompt = input_data.get("system_prompt", "")
    user_message = input_data.get("user_message", {})

    prompt = f"{system_prompt}\n\nUSER INPUT:\n{json.dumps(user_message)}"

    outputs = llm_pipeline(prompt, max_new_tokens=512, do_sample=True, temperature=0.2)
    return outputs[0]["generated_text"]
