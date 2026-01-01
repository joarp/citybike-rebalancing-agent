import sys
import os
import pandas as pd
import json

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bike_agent.tools import registry

# -------------------------------
# MOCK TOOLS
# -------------------------------

def mock_get_nearby_stations(k=5, radius_km=3.0):
    """Return fake nearby stations"""
    data = [
        {"id": f"S{i+1}", "latitude": 39.56+i*0.001, "longitude": 2.65+i*0.001,
         "free_bikes": 5+i, "empty_slots": 5+i}
        for i in range(k)
    ]
    return pd.DataFrame(data)

def mock_get_station_features(station_id):
    """Return fake features"""
    return {"id": station_id, "name": f"Station {station_id}", "bikes": 5, "slots": 5}

def mock_get_distances(station_ids):
    """Return simple distance matrix (1 km between consecutive stations)"""
    import numpy as np
    df = pd.DataFrame(
        np.abs(np.subtract.outer(range(len(station_ids)), range(len(station_ids)))),
        index=station_ids,
        columns=station_ids
    )
    return df

def mock_validate_plan(plan_json):
    """Fake validation: allow all plans"""
    return []

def mock_score_plan(plan_json):
    """Fake scoring: sum of bikes moved"""
    return sum(stop["bikes"] for stop in plan_json["stops"])

# Override the registry with mocks
registry.TOOL_REGISTRY["get_nearby_stations"] = mock_get_nearby_stations
registry.TOOL_REGISTRY["get_station_features"] = mock_get_station_features
registry.TOOL_REGISTRY["get_distances"] = mock_get_distances
registry.TOOL_REGISTRY["validate_plan"] = mock_validate_plan
registry.TOOL_REGISTRY["score_plan"] = mock_score_plan

# -------------------------------
# MOCK LLM
# -------------------------------

def mock_llm(input_data):
    context = input_data.get("user_message", {})

    # Step 1: Request nearby stations
    if "nearby_stations" not in context.get("context", {}):
        return json.dumps({
            "type": "TOOL_REQUEST",
            "tool": "get_nearby_stations",
            "args": {"k": 6, "radius_km": 3.0}
        })

    # Step 2: Propose complex plan (multiple pickups/dropoffs)
    if "approved_plan" not in context:
        stations = context["context"]["nearby_stations"]
        if len(stations) >= 4:
            plan = {
                "type": "PLAN",
                "assumptions": {"truck_capacity": 15, "time_budget_min": 180},
                "stops": [
                    {"station_id": stations[0]["id"], "action": "pickup", "bikes": 4},
                    {"station_id": stations[1]["id"], "action": "pickup", "bikes": 3},
                    {"station_id": stations[2]["id"], "action": "dropoff", "bikes": 5},
                    {"station_id": stations[3]["id"], "action": "dropoff", "bikes": 2}
                ]
            }
            return json.dumps(plan)

    # Step 3: Return FINAL instructions
    if "approved_plan" in context:
        approved_plan = context["approved_plan"]
        instructions = []
        for stop in approved_plan["stops"]:
            action = "pick up" if stop["action"] == "pickup" else "drop off"
            instructions.append(f"{action.capitalize()} {stop['bikes']} bikes at station {stop['station_id']}")
        return f"FINAL\n" + "\n".join(instructions)

    # Default fallback
    return json.dumps({"type": "FINAL", "instructions": "No instructions available"})

# -------------------------------
# ORCHESTRATOR TEST LOOP
# -------------------------------

def test_orchestrator():
    context = {
        "start": {"lat": 39.566056, "lon": 2.659389},
        "truck_capacity": 15,
        "time_budget_min": 180,
        "context": {}
    }

    while True:
        llm_input = {"system_prompt": "SYSTEM_PROMPT_PLACEHOLDER", "user_message": context}
        llm_output = mock_llm(llm_input)

        # If FINAL instructions
        if not llm_output.strip().startswith("{"):
            print("===== FINAL INSTRUCTIONS =====")
            print(llm_output)
            break

        output_json = json.loads(llm_output)
        output_type = output_json.get("type")

        if output_type == "TOOL_REQUEST":
            tool_name = output_json["tool"]
            args = output_json.get("args", {})
            tool = registry.get_tool(tool_name)
            result = tool(**args)
            context.setdefault("context", {})["nearby_stations"] = result.to_dict(orient="records")
            print(f"[TOOL_REQUEST] {tool_name} called, got {len(result)} records")

        elif output_type == "PLAN":
            validate = registry.get_tool("validate_plan")
            errors = validate(output_json)
            if errors:
                context["validation_errors"] = errors
                print(f"[PLAN] Validation errors: {errors}")
            else:
                context["approved_plan"] = output_json
                print(f"[PLAN] Plan approved: {output_json}")

        elif output_type == "FINAL":
            print("===== FINAL INSTRUCTIONS =====")
            print(output_json.get("instructions", "No instructions"))
            break

        else:
            print(f"[WARNING] Unknown output type: {output_type}")
            break

# -------------------------------
# RUN TEST
# -------------------------------
if __name__ == "__main__":
    test_orchestrator()
