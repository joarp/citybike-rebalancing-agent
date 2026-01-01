# bike_agent/agent/orchestrator.py
import json
import pandas as pd
from bike_agent.tools.registry import get_tool
from bike_agent.agent.llm_client import call_llm
from bike_agent.agent.system_prompt import SYSTEM_PROMPT

def optimize_route(station_ids, start_id, coords_df):
    get_distances = get_tool("get_distances")
    dist_matrix = get_distances(coords_df)

    unvisited = set(station_ids) - {start_id}
    route = []
    current = start_id

    while unvisited:
        nearest = min(unvisited, key=lambda x: dist_matrix.loc[current, x])
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest

    return route


def orchestrator(task_payload):
    user_context = task_payload.copy()

    # --- Nearby stations ---
    get_nearby_stations = get_tool("get_nearby_stations")
    nearby_df = get_nearby_stations(k=10, radius_km=3.0)
    user_context.setdefault("context", {})["nearby_stations"] = nearby_df.to_dict(orient="records")

    # --- Optimize route ---
    station_ids = list(nearby_df["id"])
    start_id = "start"

    start_coords = {
        "lat": task_payload["start"]["lat"],
        "lon": task_payload["start"]["lon"]
    }

    # Add pseudo-start to coords dataframe
    start_row = pd.DataFrame([{
        "id": start_id,
        "lat": start_coords["lat"],
        "lon": start_coords["lon"]
    }])

    nearby_with_start = pd.concat([nearby_df, start_row], ignore_index=True)
    nearby_with_start.set_index("id", inplace=True)

    route_order = optimize_route(station_ids, start_id, nearby_with_start)
    user_context["context"]["optimized_station_order"] = route_order

    # --- Main loop for LLM interaction ---
    while True:
        llm_input = {
            "system_prompt": SYSTEM_PROMPT,
            "user_message": user_context
        }

        llm_output = call_llm(llm_input)

        try:
            output_json = json.loads(llm_output)
        except json.JSONDecodeError:
            # Not JSON → assume final instructions
            print("FINAL INSTRUCTIONS:")
            print(llm_output)
            break

        if output_json["type"] == "TOOL_REQUEST":
            tool_name = output_json["tool"]
            args = output_json.get("args", {})
            tool = get_tool(tool_name)
            tool_result = tool(**args)
            user_context.setdefault("context", {})[tool_name] = tool_result

        elif output_json["type"] == "PLAN":
            validate_tool = get_tool("validate_plan")
            errors = validate_tool(output_json)
            if errors:
                user_context["validation_errors"] = errors
            else:
                user_context["approved_plan"] = output_json

        elif output_json["type"] == "FINAL":
            print("FINAL INSTRUCTIONS:")
            print(output_json.get("instructions", "No instructions field"))
            break

        else:
            raise ValueError(f"Unknown LLM output type: {output_json['type']}")

    return user_context
