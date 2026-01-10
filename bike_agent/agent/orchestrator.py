import json
import pandas as pd
from bike_agent.tools.registry import get_tool
from bike_agent.agent.llm_client import call_llm
from bike_agent.agent.system_prompt import SYSTEM_PROMPT
from bike_agent.tools.registry import get_tool_spec
from bike_agent.agent.tool_calling import coerce_args, validate_args_against_signature
from bike_agent.agent.prompt_tools import build_tool_catalog
from bike_agent.tools.validate_plan import validate_plan


def serialize_tool_result(result):
    if isinstance(result, pd.DataFrame):
        return result.to_dict(orient="records")
    if isinstance(result, (list, dict)):
        return result
    return str(result)

def orchestrator(task_payload):
    user_context = task_payload.copy()

    # Build tool catalog 
    tool_catalog_text = build_tool_catalog()
    # Replace the placeholder token in system prompt
    UPDATED_SYSTEM_PROMPT = SYSTEM_PROMPT.replace("__TOOLS__", tool_catalog_text)

    # --- Main loop for LLM interaction ---
    MAX_STEPS = 20
    for step in range(1, MAX_STEPS + 1):
        print(f"\n=== STEP {step} ===")
        llm_input = {
            "system_prompt": UPDATED_SYSTEM_PROMPT,
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
            raw_args = output_json.get("args", {})
            print(f"EXECUTING: {tool_name} WITH args: {raw_args}")
            spec = get_tool_spec(tool_name)          # raises if unknown
            tool_fn = spec.fn

            try:
                args = coerce_args(raw_args, spec.arg_types)
                validate_args_against_signature(tool_fn, args)

                tool_result = tool_fn(**args)
                serialized = serialize_tool_result(tool_result)

                user_context.setdefault("context", {})[tool_name] = serialized

            except Exception as e:
                user_context.setdefault("context", {})["tool_error"] = {
                    "tool": tool_name,
                    "error": f"{type(e).__name__}: {e}",
                    "raw_args": raw_args,
                }

        elif output_json["type"] == "PLAN":
            # print("CONTT:")
            # print(user_context["context"])
            errors = validate_plan(output_json, user_context["context"])
            if errors:
                print(f"[VALIDATION ERRORS] {errors}")
                user_context["validation_errors"] = errors
            else:
                print("[PLAN APPROVED] Plan is valid. Format output.")
                user_context["approved_plan"] = output_json
                user_context["task"] = "FINALIZE"
                print(user_context)
                return format_final_instructions(user_context)

        else:
            raise ValueError(f"Unknown LLM output type: {output_json['type']}")

    else:
        raise RuntimeError("Agent did not converge within MAX_STEPS")

    return json.dumps(user_context, indent=2, ensure_ascii=False)


def format_final_instructions(payload):
    plan = payload["approved_plan"]

    # Only change: read stations from your actual key: context["get_nearby_stations"]
    stations = {
        s["id"]: s for s in payload["context"]["get_nearby_stations"]
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

        # Only change: avoid formatting error if dist is "?"
        dist_str = f"{dist:.2f}" if isinstance(dist, (int, float)) else "?"

        lines.append(
            f"{i}️⃣ Station {station_short_id} ({dist_str} km)\n"
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
