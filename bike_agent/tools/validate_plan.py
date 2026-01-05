# validate_plan.py
#from .get_nearby_stations import get_nearby_stations
import json

# def validate_plan(plan_json):
#     """
#     Validate a plan for:
#     - Truck capacity
#     - Non-negative pickups/drops
#     - Station availability
#     Returns a list of validation errors.
#     """
#     errors = []
#     truck_capacity = plan_json["assumptions"]["truck_capacity"]
#     total_bikes = 0

#     for stop in plan_json["stops"]:
#         bikes = stop["bikes"]
#         if bikes < 0:
#             errors.append({"code": "NEGATIVE_BIKES", "detail": f"Bikes cannot be negative at {stop['station_id']}"})
#         if stop["action"] == "pickup":
#             total_bikes += bikes
#         elif stop["action"] == "dropoff":
#             total_bikes -= bikes

#     if total_bikes > truck_capacity:
#         errors.append({"code": "CAPACITY_EXCEEDED", "detail": f"Total picked up {total_bikes} exceeds truck_capacity {truck_capacity}"})

#     # Optional: check station availability (simplified)
#     for stop in plan_json["stops"]:
#         nearby = get_nearby_stations(100, 100)  # large k/radius to get all stations
#         station = nearby[nearby["id"] == stop["station_id"]]
#         if not station.empty:
#             free_bikes = station.iloc[0]["free_bikes"]
#             empty_slots = station.iloc[0]["empty_slots"]
#             if stop["action"] == "pickup" and stop["bikes"] > free_bikes:
#                 errors.append({"code": "PICKUP_EXCEEDS_AVAILABLE", "detail": f"Pickup {stop['bikes']} from {stop['station_id']} but only {free_bikes} available"})
#             if stop["action"] == "dropoff" and stop["bikes"] > empty_slots:
#                 errors.append({"code": "DROPOFF_EXCEEDS_CAPACITY", "detail": f"Dropoff {stop['bikes']} to {stop['station_id']} but only {empty_slots} empty slots"})

#     return errors

def validate_plan(plan_json, context):
    """
    Pure validation:
    - No tool calls
    - Uses only provided context
    - Deterministic
    """

    errors = []

    assumptions = plan_json.get("assumptions", {})
    truck_capacity = assumptions.get("truck_capacity")

    if truck_capacity is None:
        errors.append({
            "code": "MISSING_TRUCK_CAPACITY",
            "detail": "truck_capacity missing from assumptions"
        })
        return errors

    # Build station state from context
    stations = {
        s["id"]: {
            "free_bikes": s["free_bikes"],
            "empty_slots": s["empty_slots"]
        }
        for s in context.get("nearby_stations", [])
    }

    current_load = 0

    for i, stop in enumerate(plan_json.get("stops", [])):
        station_id = stop.get("station_id")
        action = stop.get("action")
        bikes = stop.get("bikes")

        if station_id not in stations:
            errors.append({
                "code": "UNKNOWN_STATION",
                "detail": f"Station {station_id} not found in context"
            })
            continue

        if bikes is None or bikes < 0:
            errors.append({
                "code": "INVALID_BIKES",
                "detail": f"Invalid bikes value at {station_id}"
            })
            continue

        station = stations[station_id]

        if action == "pickup":
            if bikes > station["free_bikes"]:
                errors.append({
                    "code": "PICKUP_EXCEEDS_AVAILABLE",
                    "detail": f"Pickup {bikes} from {station_id}, only {station['free_bikes']} available"
                })
            current_load += bikes
            station["free_bikes"] -= bikes
            station["empty_slots"] += bikes

        elif action == "dropoff":
            if bikes > station["empty_slots"]:
                errors.append({
                    "code": "DROPOFF_EXCEEDS_CAPACITY",
                    "detail": f"Dropoff {bikes} to {station_id}, only {station['empty_slots']} slots available"
                })
            current_load -= bikes
            station["free_bikes"] += bikes
            station["empty_slots"] -= bikes

        else:
            errors.append({
                "code": "INVALID_ACTION",
                "detail": f"Invalid action '{action}' at {station_id}"
            })
            continue

        if current_load < 0:
            errors.append({
                "code": "NEGATIVE_TRUCK_LOAD",
                "detail": f"Truck load became negative after stop {i}"
            })

        if current_load > truck_capacity:
            errors.append({
                "code": "CAPACITY_EXCEEDED",
                "detail": f"Truck load {current_load} exceeds capacity {truck_capacity} at stop {i}"
            })

    return errors
