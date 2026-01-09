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
    nearby_df = get_nearby_stations(k=10, radius_km=3.0, lat=start_coords["lat"], lon=start_coords["lon"])
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
                return format_final_instructions(user_context)

        elif output_json["type"] == "FINAL":
            print("[FINAL OUTPUT]")
            print(output_json.get("instructions", "No instructions field"))
            break

        else:
            raise ValueError(f"Unknown LLM output type: {output_json['type']}")

    else:
        raise RuntimeError("Agent did not converge within MAX_STEPS")

    return json.dumps(user_context, indent=2, ensure_ascii=False)


def format_final_instructions(payload):
    plan = payload["approved_plan"]
    stations = {
        s["id"]: s for s in payload["context"]["nearby_stations"]
    }

    lines = []
    lines.append("🚚 Citybike Rebalancing Route (2 hours)\n")

    start = payload["start_coordinates"]
    lines.append(
        f"Start location:\n📍 {start['lat']:.5f}, {start['lon']:.5f}\n"
    )

    assumptions = plan["assumptions"]
    lines.append(
        f"Truck capacity: {assumptions['truck_capacity']} bikes\n"
        f"Time budget: {assumptions['time_budget_min']} minutes\n"
    )

    lines.append("─" * 28)
    lines.append("\n🔄 Rebalancing instructions\n")

    for i, stop in enumerate(plan["stops"], start=1):
        station = stations.get(stop["station_id"], {})
        dist = station.get("distance_km", "?")

        action = "➕ Pick up" if stop["action"] == "pickup" else "➖ Drop off"
        bikes = stop["bikes"]

        station_short_id = stop["station_id"][:4]

        lines.append(
            f"{i}️⃣ Station {station_short_id} ({dist:.2f} km)\n"
            f"   {action} {bikes} bikes\n"
        )

    lines.append("─" * 28)
    lines.append(
        "\n✅ Result\n"
        f"• {len(plan['stops'])} stations rebalanced\n"
        "• Truck load kept within capacity\n"
        "• Route optimized for distance\n\n"
        "Drive safely! 🚦"
    )

    return "\n".join(lines)
