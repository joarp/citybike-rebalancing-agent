# import json
# import pandas as pd
# from bike_agent.tools.registry import get_tool
# from bike_agent.agent.llm_client import call_llm
# from bike_agent.agent.system_prompt import SYSTEM_PROMPT

# def optimize_route(station_ids, start_id, coords_df):
#     get_distances = get_tool("get_distances")
#     dist_matrix = get_distances(coords_df)

#     unvisited = set(station_ids) - {start_id}
#     route = []
#     current = start_id

#     while unvisited:
#         nearest = min(unvisited, key=lambda x: dist_matrix.loc[current, x])
#         route.append(nearest)
#         unvisited.remove(nearest)
#         current = nearest

#     return route

# def serialize_tool_result(result):
#     if isinstance(result, pd.DataFrame):
#         return result.to_dict(orient="records")
#     if isinstance(result, (list, dict)):
#         return result
#     return str(result)

# def orchestrator(task_payload):
#     user_context = task_payload.copy()

#     # --- Extract start coordinates ---
#     start_coords = task_payload["start_coordinates"]
#     start_id = "start"

#     # --- Nearby stations ---
#     get_nearby_stations = get_tool("get_nearby_stations")
#     nearby_df = get_nearby_stations(k=10, radius_km=3.0)
#     user_context.setdefault("context", {})["nearby_stations"] = nearby_df.to_dict(orient="records")

#     # --- Optimize route ---
#     station_ids = list(nearby_df["id"])
#     start_row = pd.DataFrame([{
#         "id": start_id,
#         "lat": start_coords["lat"],
#         "lon": start_coords["lon"]
#     }])
#     nearby_with_start = pd.concat([nearby_df, start_row], ignore_index=True)
#     nearby_with_start.set_index("id", inplace=True)
#     route_order = optimize_route(station_ids, start_id, nearby_with_start)
#     user_context["context"]["optimized_station_order"] = route_order

#     # --- Main loop for LLM interaction ---
#     MAX_STEPS = 20
#     for step in range(MAX_STEPS):
#         print(f"\n=== STEP {step + 1} ===")
#         llm_input = {
#             "system_prompt": SYSTEM_PROMPT,
#             "user_message": user_context
#         }

#         llm_output = call_llm(llm_input)

#         # Try to parse LLM output as JSON
#         try:
#             output_json = json.loads(llm_output)
#         except json.JSONDecodeError:
#             # Non-JSON → assume FINAL instructions
#             print("[LLM FINAL INSTRUCTIONS]")
#             print(llm_output)
#             break

#         output_type = output_json.get("type")
#         print(f"[LLM OUTPUT TYPE]: {output_type}")

#         if output_type == "TOOL_REQUEST":
#             tool_name = output_json["tool"]
#             args = output_json.get("args", {})
#             tool = get_tool(tool_name)
#             tool_result = tool(**args)
#             user_context.setdefault("context", {})[tool_name] = serialize_tool_result(tool_result)
#             print(f"[TOOL_REQUEST] {tool_name} -> result stored in context")

#         elif output_type == "PLAN":
#             validate_tool = get_tool("validate_plan")
#             errors = validate_tool(output_json, user_context["context"])

#             if errors:
#                 user_context["validation_errors"] = errors
#                 print(f"[PLAN VALIDATION ERRORS]: {errors}")
#             else:
#                 user_context["approved_plan"] = output_json
#                 user_context["task"] = "FINALIZE"
#                 print("[PLAN APPROVED] Plan is valid. Moving to FINAL.")
#                 break  # stop calling LLM once a valid plan is reached

#         elif output_type == "FINAL":
#             print("[FINAL INSTRUCTIONS]")
#             print(output_json.get("instructions", "No instructions provided"))
#             break

#         else:
#             raise ValueError(f"Unknown LLM output type: {output_type}")

#     else:
#         # Only triggered if loop hits MAX_STEPS without break
#         raise RuntimeError("Agent did not converge within MAX_STEPS")

#     return user_context
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

def serialize_tool_result(result):
    if isinstance(result, pd.DataFrame):
        return result.to_dict(orient="records")
    if isinstance(result, (list, dict)):
        return result
    return str(result)

def orchestrator(task_payload):
    user_context = task_payload.copy()

    # --- Start coordinates ---
    start_coords = {
        "lat": task_payload["start_coordinates"]["lat"],
        "lon": task_payload["start_coordinates"]["lon"]
    }

    # --- Nearby stations ---
    get_nearby_stations = get_tool("get_nearby_stations")
    nearby_df = get_nearby_stations(k=10, radius_km=3.0)
    user_context.setdefault("context", {})["nearby_stations"] = nearby_df.to_dict(orient="records")

    # --- Optimize route ---
    station_ids = list(nearby_df["id"])
    start_id = "start"
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
    MAX_STEPS = 20

    for step in range(1, MAX_STEPS + 1):
        print(f"\n=== STEP {step} ===")
        llm_input = {
            "system_prompt": SYSTEM_PROMPT,
            "user_message": user_context
        }

        llm_output = call_llm(llm_input)

        try:
            output_json = json.loads(llm_output)
            output_type = output_json.get("type", "UNKNOWN")
            print(f"[LLM OUTPUT TYPE]: {output_type}")
        except json.JSONDecodeError:
            print("LLM returned non-JSON output (assuming FINAL instructions):")
            print(llm_output)
            break

        if output_json["type"] == "TOOL_REQUEST":
            tool_name = output_json["tool"]
            args = output_json.get("args", {})
            print(f"[TOOL REQUEST] {tool_name} with args {args}")
            tool = get_tool(tool_name)
            tool_result = tool(**args)
            serialized_result = serialize_tool_result(tool_result)
            print(f"[TOOL RESULT] {tool_name}: {serialized_result}")
            user_context.setdefault("context", {})[tool_name] = serialized_result

        elif output_json["type"] == "PLAN":
            validate_tool = get_tool("validate_plan")
            errors = validate_tool(output_json, user_context["context"])
            if errors:
                print(f"[VALIDATION ERRORS] {errors}")
                user_context["validation_errors"] = errors
            else:
                print("[PLAN APPROVED] Plan is valid. Moving to FINAL.")
                user_context["approved_plan"] = output_json
                user_context["task"] = "FINALIZE"
                break

        elif output_json["type"] == "FINAL":
            print("[FINAL OUTPUT]")
            print(output_json.get("instructions", "No instructions field"))
            break

        else:
            raise ValueError(f"Unknown LLM output type: {output_json['type']}")

    else:
        raise RuntimeError("Agent did not converge within MAX_STEPS")

    return user_context
