# # tests/test_full_agentic.py
# from bike_agent.agent.orchestrator import orchestrator

# def main():
#     task_payload = {
#         "task": "PLAN_ROUTE",
#         "start_coordinates": {"lat": 59.3293, "lon": 18.0686}
#     }

#     print("Running full agentic workflow with real LLM...")
#     result = orchestrator(task_payload)
#     print("Final output:")
#     print(result)

# if __name__ == "__main__":
#     main()
# tests/test_full_agentic.py
from bike_agent.agent.orchestrator import orchestrator

def main():
    task_payload = {
        "task": "PLAN_ROUTE",
        "start_coordinates": {"lat": 59.3293, "lon": 18.0686}
    }

    print("=== Running full agentic workflow with real LLM ===")
    print(f"Start coordinates: {task_payload['start_coordinates']}\n")

    try:
        result = orchestrator(task_payload)
    except RuntimeError as e:
        print(f"\n[ERROR] Agent did not converge: {e}")
        result = None

    print("\n=== FINAL OUTPUT ===")
    if result is None:
        print("No plan produced due to non-convergence.")
    else:
        approved_plan = result.get("approved_plan")
        if approved_plan:
            print("Approved PLAN:")
            for stop in approved_plan.get("stops", []):
                print(f"  - {stop['action']} {stop['bikes']} bikes at station {stop['station_id']}")
        else:
            final_instructions = result.get("instructions")
            if final_instructions:
                print(final_instructions)
            else:
                print(result)

if __name__ == "__main__":
    main()
