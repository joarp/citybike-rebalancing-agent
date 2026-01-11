import json
import pandas as pd

from bike_agent.agent.llm_client import call_llm
from bike_agent.agent.system_prompt import SYSTEM_PROMPT, CRITIC_SYSTEM_PROMPT

from bike_agent.tools.registry import get_tool_spec
from bike_agent.agent.tool_calling import coerce_args, validate_args_against_signature
from bike_agent.agent.prompt_tools import build_tool_catalog

from bike_agent.tools.validate_plan import validate_plan
from bike_agent.tools.score_plan import score_plan


def serialize_tool_result(result):
    if isinstance(result, pd.DataFrame):
        return result.to_dict(orient="records")

    if isinstance(result, dict):
        return {k: serialize_tool_result(v) for k, v in result.items()}

    if isinstance(result, (list, tuple)):
        return [serialize_tool_result(x) for x in result]

    try:
        import numpy as np
        if isinstance(result, (np.integer, np.floating)):
            return result.item()
    except Exception:
        pass

    return result


def critic_llm(*, context: dict, plan: dict, score: dict, max_low_threshold: int = 3) -> dict:
    print("\n[CRITIC] Calling critic LLM")
    print(f"[CRITIC] Current score: {score.get('score')}")

    critic_user_message = {
        "context": context,
        "plan": plan,
        "score": score,
    }

    llm_input = {
        "system_prompt": CRITIC_SYSTEM_PROMPT,
        "user_message": critic_user_message,
    }
    llm_output = call_llm(llm_input)

    try:
        out = json.loads(llm_output)
    except json.JSONDecodeError:
        print("[CRITIC] Non-JSON output → APPROVED")
        return {
            "type": "APPROVED",
            "reason": "Critic returned non-JSON output; passing through current plan.",
            "expected_score_delta": 0,
        }

    print(f"[CRITIC] Output type: {out.get('type')}")
    print(f"[CRITIC] Expected score delta: {out.get('expected_score_delta')}")

    t = out.get("type")
    if t == "APPROVED":
        try:
            delta = int(out.get("expected_score_delta", 0))
        except Exception:
            delta = 0
        out["expected_score_delta"] = max(0, delta)
        out.setdefault("reason", "Approved.")
        print("[CRITIC] Plan approved")
        return out

    if t == "PLAN":
        if "assumptions" not in out or "stops" not in out:
            print("[CRITIC] Invalid PLAN structure → APPROVED")
            return {
                "type": "APPROVED",
                "reason": "Critic PLAN missing required fields; passing through current plan.",
                "expected_score_delta": 0,
            }

        try:
            delta = int(out.get("expected_score_delta", 1))
        except Exception:
            delta = 1
        out["expected_score_delta"] = max(0, delta)
        out.setdefault("reason", "Revised plan.")
        print("[CRITIC] Revised PLAN proposed")
        return out

    print("[CRITIC] Unknown output type → APPROVED")
    return {
        "type": "APPROVED",
        "reason": f"Critic returned unknown type '{t}'; passing through current plan.",
        "expected_score_delta": 0,
    }


def planner_step(user_context: dict, updated_system_prompt: str, max_steps: int = 20) -> dict:
    print("\n[PLANNER] Starting planner loop")

    for step in range(1, max_steps + 1):
        print(f"\n[PLANNER] Step {step}/{max_steps}")

        llm_input = {"system_prompt": updated_system_prompt, "user_message": user_context}
        llm_output = call_llm(llm_input)

        try:
            output_json = json.loads(llm_output)
        except json.JSONDecodeError:
            raise RuntimeError(f"Planner returned non-JSON output:\n{llm_output}")

        out_type = output_json.get("type")
        print(f"[PLANNER] Output type: {out_type}")

        if out_type == "TOOL_REQUEST":
            tool_name = output_json["tool"]
            print(f"[PLANNER] TOOL_REQUEST → {tool_name}")

            raw_args = output_json.get("args", {})
            spec = get_tool_spec(tool_name)
            tool_fn = spec.fn

            args = coerce_args(raw_args, spec.arg_types)
            validate_args_against_signature(tool_fn, args)

            tool_result = tool_fn(**args)
            serialized = serialize_tool_result(tool_result)

            ctx = user_context.setdefault("context", {})
            ctx[tool_name] = serialized
            if tool_name == "get_nearby_stations":
                ctx["nearby_stations"] = serialized

            continue

        if out_type == "PLAN":
            ctx = user_context.setdefault("context", {})
            errors = validate_plan(output_json, ctx)
            if errors:
                print("[PLANNER] Validation errors → retrying")
                print(errors)
                user_context["validation_errors"] = errors
                continue

            print("[PLANNER] Valid PLAN found")
            return output_json

        raise ValueError(f"Unknown planner output type: {out_type}")

    raise RuntimeError("Planner did not produce a valid plan within max_steps")


def improve_with_critic(
    *,
    context: dict,
    initial_plan: dict,
    max_revisions: int = 3,
    low_threshold: int = 3
) -> tuple[dict, dict]:
    print("\n[CRITIC LOOP] Starting critic revision loop")

    print("INITIAL----PLAN")
    print(initial_plan)
    best_plan = initial_plan
    best_score_obj = score_plan(best_plan, context, low_threshold=low_threshold)
    best_score = best_score_obj.get("score", 0)

    print(f"[CRITIC LOOP] Initial score: {best_score}")

    for r in range(max_revisions):
        print(f"\n[CRITIC LOOP] Revision {r + 1}/{max_revisions}")

        critic_out = critic_llm(
            context=context,
            plan=best_plan,
            score=best_score_obj,
            max_low_threshold=low_threshold,
        )

        print("CRITIC----PLAN")
        print(critic_out)

        ctype = critic_out.get("type")
        print(f"[CRITIC LOOP] Critic output type: {ctype}")

        if ctype == "APPROVED":
            print("[CRITIC LOOP] Approved → stopping revisions")
            return best_plan, best_score_obj

        if ctype != "PLAN":
            print("[CRITIC LOOP] Unexpected output → stopping revisions")
            return best_plan, best_score_obj

        errors = validate_plan(critic_out, context)
        if errors:
            print("[CRITIC LOOP] Revised plan invalid → continuing (errors added to context)")
            print(errors)
            # Add errors to context so critic can fix next iteration
            context["critic_validation_errors"] = errors
            context["critic_last_invalid_plan"] = critic_out
            continue
        else:
            # Clear critic error feedback if we got a valid plan
            if "critic_validation_errors" in context:
                context["critic_validation_errors"] = []
            if "critic_last_invalid_plan" in context:
                context["critic_last_invalid_plan"] = None

            cand_score_obj = score_plan(critic_out, context, low_threshold=low_threshold)
            cand_score = cand_score_obj.get("score", 0)

            if cand_score >= best_score:
                best_score_obj = cand_score_obj
                best_score = cand_score
                best_plan = critic_out

    print("[CRITIC LOOP] Max revisions reached")
    return best_plan, best_score_obj


def orchestrator(task_payload):
    print("\n[ORCHESTRATOR] Starting orchestration")

    user_context = task_payload.copy()
    tool_catalog_text = build_tool_catalog()
    UPDATED_SYSTEM_PROMPT = SYSTEM_PROMPT.replace("__TOOLS__", tool_catalog_text)

    plan = planner_step(user_context, UPDATED_SYSTEM_PROMPT, max_steps=20)

    ctx = user_context.setdefault("context", {})
    best_plan, best_score_obj = improve_with_critic(
        context=ctx,
        initial_plan=plan,
        max_revisions=4,
        low_threshold=3,
    )

    print("\n[ORCHESTRATOR] Final plan approved")
    print(f"[ORCHESTRATOR] Final score: {best_score_obj.get('score')}")

    user_context["approved_plan"] = best_plan
    user_context["approved_score"] = best_score_obj
    return format_final_instructions(user_context)



def format_final_instructions(payload):
    plan = payload["approved_plan"]
    context = payload.get("context", {})

    # Build distance lookup if available
    distances = context.get("get_distances", {})
    pair_lookup = {}
    if isinstance(distances, dict):
        for p in distances.get("pairs", []):
            a, b = p.get("from"), p.get("to")
            if a and b:
                pair_lookup[(a, b)] = p
                pair_lookup[(b, a)] = p  # treat as undirected

    def leg_info(frm, to):
        p = pair_lookup.get((frm, to))
        if not p:
            return None
        d = p.get("distance_km")
        t = p.get("duration_min")
        if isinstance(d, (int, float)) and isinstance(t, (int, float)):
            return f"{d:.2f} km · {t:.1f} min"
        return None

    lines = []
    lines.append("🚚 Citybike Rebalancing Route\n")

    start = payload.get("start_coordinates", {})
    if "lat" in start and "lon" in start:
        lines.append(f"Start location:\n📍 {start['lat']:.5f}, {start['lon']:.5f}\n")
    else:
        lines.append("Start location:\n📍 (missing)\n")

    assumptions = plan.get("assumptions", {})
    lines.append(
        f"Truck capacity: {assumptions.get('truck_capacity', '?')} bikes\n"
        f"Time budget: {assumptions.get('time_budget_min', '?')} minutes\n"
    )

    lines.append("─" * 28)
    lines.append("\n🔄 Rebalancing instructions\n")

    prev_id = "start"

    for i, stop in enumerate(plan.get("stops", []), start=1):
        sid = stop.get("station_id", "????")
        action = "➕ Pick up" if stop.get("action") == "pickup" else "➖ Drop off"
        bikes = stop.get("bikes", "?")

        # Travel leg (if available)
        leg = leg_info(prev_id, sid)
        if leg:
            lines.append(f"➡️  Drive: {leg}\n")

        lines.append(
            f"{i}️⃣ Station {str(sid)[:4]}\n"
            f"   {action} {bikes} bikes\n"
        )

        prev_id = sid

    lines.append("─" * 28)
    lines.append(
        "\n✅ Result\n"
        f"• {len(plan.get('stops', []))} stations rebalanced\n"
        "• Truck load kept within capacity\n\n"
        "Drive safely! 🚦"
    )

    return "\n".join(lines)
