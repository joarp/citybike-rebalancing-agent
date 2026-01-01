# validate_plan.py
from .get_nearby_stations import get_nearby_stations
import json

def validate_plan(plan_json):
    """
    Validate a plan for:
    - Truck capacity
    - Non-negative pickups/drops
    - Station availability
    Returns a list of validation errors.
    """
    errors = []
    truck_capacity = plan_json["assumptions"]["truck_capacity"]
    total_bikes = 0

    for stop in plan_json["stops"]:
        bikes = stop["bikes"]
        if bikes < 0:
            errors.append({"code": "NEGATIVE_BIKES", "detail": f"Bikes cannot be negative at {stop['station_id']}"})
        if stop["action"] == "pickup":
            total_bikes += bikes
        elif stop["action"] == "dropoff":
            total_bikes -= bikes

    if total_bikes > truck_capacity:
        errors.append({"code": "CAPACITY_EXCEEDED", "detail": f"Total picked up {total_bikes} exceeds truck_capacity {truck_capacity}"})

    # Optional: check station availability (simplified)
    for stop in plan_json["stops"]:
        nearby = get_nearby_stations(100, 100)  # large k/radius to get all stations
        station = nearby[nearby["id"] == stop["station_id"]]
        if not station.empty:
            free_bikes = station.iloc[0]["free_bikes"]
            empty_slots = station.iloc[0]["empty_slots"]
            if stop["action"] == "pickup" and stop["bikes"] > free_bikes:
                errors.append({"code": "PICKUP_EXCEEDS_AVAILABLE", "detail": f"Pickup {stop['bikes']} from {stop['station_id']} but only {free_bikes} available"})
            if stop["action"] == "dropoff" and stop["bikes"] > empty_slots:
                errors.append({"code": "DROPOFF_EXCEEDS_CAPACITY", "detail": f"Dropoff {stop['bikes']} to {stop['station_id']} but only {empty_slots} empty slots"})

    return errors
