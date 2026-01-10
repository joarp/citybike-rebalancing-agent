import inspect
from bike_agent.tools.registry import list_tools, get_tool_spec

def _type_hint_str(arg_types: dict) -> str:
    # Pretty-print minimal coercion tags (int/float/list/str/dataframe_records/etc.)
    if not arg_types:
        return ""
    parts = [f"{k}:{v}" for k, v in arg_types.items()]
    return "  Types: " + ", ".join(parts)

def build_tool_catalog(max_tools: int | None = None) -> str:
    """
    Build a prompt-friendly tool catalog from registry ToolSpecs.
    Uses tool name + callable signature + description + coercion tags.
    """
    tool_names = sorted(list_tools())
    if max_tools is not None:
        tool_names = tool_names[:max_tools]

    lines = []
    for name in tool_names:
        spec = get_tool_spec(name)
        fn = spec.fn

        # Get real Python signature: (k, radius_km, lat, lon) etc.
        try:
            sig = str(inspect.signature(fn))
        except (TypeError, ValueError):
            sig = "(...)"

        desc = (spec.description or "").strip()
        types = _type_hint_str(spec.arg_types)

        # One compact block per tool
        lines.append(f"• {name}{sig}")
        if desc:
            lines.append(f"  → {desc}")
        if types:
            lines.append(types)

    return "\n".join(lines)
