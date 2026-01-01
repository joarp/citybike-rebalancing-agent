# score_plan.py

def score_plan(plan_json):
    """
    Simple scoring: sum of bikes moved successfully.
    Can be replaced with more sophisticated heuristics.
    """
    score = sum(stop["bikes"] for stop in plan_json["stops"])
    return score
