# mocked example of full loop

import sys
import os

# Add project root (parent of tests/) to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bike_agent.tools.registry import get_tool  # should now work



# Nearby stations
nearby = get_tool("get_nearby_stations")(k=5, radius_km=3.0)
print(nearby)

# Validate plan
plan = {
    "assumptions": {"truck_capacity": 10, "time_budget_min": 120},
    "stops": [
        {"station_id": "S1", "action": "pickup", "bikes": 5},
        {"station_id": "S2", "action": "dropoff", "bikes": 5}
    ]
}
errors = get_tool("validate_plan")(plan)
print(errors)

# Score plan
score = get_tool("score_plan")(plan)
print(score)