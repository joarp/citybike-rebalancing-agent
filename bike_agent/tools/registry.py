# bike_agent/tools/registry.py

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

# Import tool callables
from .get_nearby_stations import get_nearby_stations
from .get_station_features import get_station_features
from .get_distances import get_distances
from .validate_plan import validate_plan
from .score_plan import score_plan


@dataclass(frozen=True)
class ToolSpec:
    fn: Callable[..., Any]
    # Minimal type tags for coercion (used by your generic tool calling layer)
    arg_types: Dict[str, str]  # e.g. {"coords_df": "dataframe_records", "k": "int"}
    description: str = ""


_TOOLS: Dict[str, ToolSpec] = {}


def register_tool(
    name: str,
    fn: Callable[..., Any],
    arg_types: Optional[Dict[str, str]] = None,
    description: str = "",
) -> None:
    if not isinstance(name, str) or not name:
        raise ValueError("Tool name must be a non-empty string.")
    if name in _TOOLS:
        raise ValueError(f"Tool '{name}' is already registered.")
    _TOOLS[name] = ToolSpec(fn=fn, arg_types=arg_types or {}, description=description)


def get_tool_spec(name: str) -> ToolSpec:
    try:
        return _TOOLS[name]
    except KeyError as e:
        raise KeyError(f"Unknown tool: {name}. Available: {sorted(_TOOLS.keys())}") from e


def get_tool(name: str):
    """Backwards-compatible: returns the callable tool function."""
    return get_tool_spec(name).fn


def list_tools():
    return list(_TOOLS.keys())


# ----------------------------
# Register tools (single source of truth)
# ----------------------------

register_tool(
    "get_nearby_stations",
    get_nearby_stations,
    arg_types={
        "k": "int",
        "radius_km": "float",
        "lat": "float",
        "lon": "float",
    },
    description=(
        "Find k nearby stations within radius_km of (lat, lon). "
        "Uses haversine distance for fast candidate selection. "
        "Use get_distances afterwards to compute driving distance/time."
    ),
)

register_tool(
    "get_station_features",
    get_station_features,
    arg_types={
        "station_id": "str",
    },
    description="Fetch features/status for a single station by station_id.",
)

register_tool(
    "get_distances",
    get_distances,
    arg_types={"stations": "list", "start_coordinates": "dict"},
    description="Compute pairwise driving distances and durations between candidate stations using OSRM. If start_coordinates is provided, includes a 'start' node in the matrices. When calling get_distances, include at most 10 stations.",
)
