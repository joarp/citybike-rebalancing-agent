# app.py
import gradio as gr
from bike_agent.agent.orchestrator import orchestrator

def run_agent(task_payload_json):
    import json
    try:
        task_payload = json.loads(task_payload_json)
    except json.JSONDecodeError:
        return "Invalid JSON"
    result = orchestrator(task_payload)
    return json.dumps(result, indent=2)

iface = gr.Interface(
    fn=run_agent,
    inputs=gr.Textbox(lines=10, label="Task Payload (JSON)"),
    outputs=gr.Textbox(lines=20, label="Output"),
    title="Citybike Rebalancing Agent"
)

if __name__ == "__main__":
    iface.launch(server_name="0.0.0.0", server_port=7860)
