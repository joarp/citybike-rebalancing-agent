# validate_plan.py
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

    nearby = context.get("nearby_stations") or context.get("get_nearby_stations") or []

    stations = {
        s["id"]: {
            "free_bikes": s.get("free_bikes", 0),
            "empty_slots": s.get("empty_slots", 0)
        }
        for s in nearby
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
