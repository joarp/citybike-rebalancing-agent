# """
# Tool registry.

# Keeps a mapping from tool name -> callable.
# Used by the agent/orchestrator to dynamically invoke tools.
# """

# from get_nearby_stations import get_nearby_stations


# TOOL_REGISTRY = {
#     "get_nearby_stations": get_nearby_stations,
# }


# def get_tool(name: str):
#     """
#     Retrieve a tool callable by name.
#     """
#     if name not in TOOL_REGISTRY:
#         raise KeyError(f"Tool '{name}' is not registered.")
#     return TOOL_REGISTRY[name]


# def list_tools():
#     """
#     List available tool names.
#     """
#     return list(TOOL_REGISTRY.keys())

# registry.py
from .get_nearby_stations import get_nearby_stations
from .get_station_features import get_station_features
from .get_distances import get_distances
from .validate_plan import validate_plan
from .score_plan import score_plan

TOOL_REGISTRY = {
    "get_nearby_stations": get_nearby_stations,
    "get_station_features": get_station_features,
    "get_distances": get_distances,
    "validate_plan": validate_plan,
    "score_plan": score_plan,
}

def get_tool(name: str):
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Tool '{name}' is not registered.")
    return TOOL_REGISTRY[name]

def list_tools():
    return list(TOOL_REGISTRY.keys())
