from bike_agent.tools.score_plan import score_plan_simple

def test_score_plan_simple():
    # Minimal but realistic context (mirrors orchestrator usage)
    context = {
        "get_nearby_stations": [
            {"id": "s1", "free_bikes": 1, "empty_slots": 15},
            {"id": "s2", "free_bikes": 5, "empty_slots": 2},
            {"id": "s3", "free_bikes": 0, "empty_slots": 20},
        ]
    }

    # Plan with mixed actions
    plan = {
        "stops": [
            {"station_id": "s1", "action": "dropoff", "bikes": 4},  # counts
            {"station_id": "s2", "action": "dropoff", "bikes": 3},  # ignored (free_bikes >= threshold)
            {"station_id": "s3", "action": "dropoff", "bikes": 2},  # counts
            {"station_id": "s1", "action": "pickup",  "bikes": 5},  # ignored (not dropoff)
        ]
    }

    result = score_plan_simple(plan, context, low_threshold=3)

    assert result["score"] == 6


# -------------------------------
# RUN TEST
# -------------------------------
if __name__ == "__main__":
    test_score_plan_simple()
