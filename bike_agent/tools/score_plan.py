def score_plan(plan_json: dict, context: dict, low_threshold: int = 3) -> dict:
    """
    Soft scoring:
    - No tool calls
    - Uses only provided context
    - Never raises due to missing context; returns warnings instead
    """
    nearby = context.get("nearby_stations") or context.get("get_nearby_stations") or []

    stations = {
        s["id"]: {
            "free_bikes": s.get("free_bikes", 0),
            "empty_slots": s.get("empty_slots", 0)
        }
        for s in nearby
    }

    score = 0

    for stop in plan_json.get("stops", []):
        if stop.get("action") != "dropoff":
            continue

        sid = stop.get("station_id")
        bikes = stop.get("bikes", 0)

        try:
            bikes = int(bikes)
        except Exception:
            bikes = 0

        st = stations.get(sid)

        before = st["free_bikes"]
        if before < low_threshold and bikes > 0:
            score += bikes

    return {
        "metric": f"dropoffs_to_stations_with_free_bikes<{low_threshold}",
        "score": score
    }
