from pathlib import Path
from dotenv import load_dotenv

# ------------------------------------------------------------------
# Load .env from project root
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# IMPORTANT: import orchestrator module (not just function) so monkeypatch works reliably
import bike_agent.agent.orchestrator as orch_mod


def test_orchestrator(monkeypatch):
    """
    Deterministic test of the full orchestrator loop:
    - Step 1: LLM requests nearby stations
    - Step 2: LLM requests distances
    - Step 3: LLM returns a PLAN that should validate and finalize
    """

    # ----------------------------
    # Fake tool outputs (stable)
    # ----------------------------
    fake_stations = [
        # Intentionally different IDs / coords / counts than your ICL examples
        {"id": "a101", "latitude": 39.56310, "longitude": 2.65340, "free_bikes": 1,  "empty_slots": 18.0, "distance_km": 0.22},
        {"id": "b202", "latitude": 39.56590, "longitude": 2.65810, "free_bikes": 14, "empty_slots": 1.0,  "distance_km": 0.48},
        {"id": "c303", "latitude": 39.56180, "longitude": 2.64890, "free_bikes": 10, "empty_slots": 3.0,  "distance_km": 0.55},
        {"id": "d404", "latitude": 39.56840, "longitude": 2.65120, "free_bikes": 2,  "empty_slots": 20.0, "distance_km": 0.60},
        {"id": "e505", "latitude": 39.56990, "longitude": 2.65760, "free_bikes": 9,  "empty_slots": 6.0,  "distance_km": 0.75},
        {"id": "f606", "latitude": 39.56070, "longitude": 2.65600, "free_bikes": 16, "empty_slots": 0.0,  "distance_km": 0.92},
        {"id": "g707", "latitude": 39.56630, "longitude": 2.64650, "free_bikes": 0,  "empty_slots": 24.0, "distance_km": 0.98},
        {"id": "h808", "latitude": 39.57110, "longitude": 2.65280, "free_bikes": 7,  "empty_slots": 12.0, "distance_km": 1.05},
    ]

    fake_distances = {
        "ids": ["start"] + [s["id"] for s in fake_stations],
        "pairs": [
            # Keep it small: your validate_plan might only need existence, not full completeness.
            {"from": "start", "to": "a101", "distance_km": 0.30, "duration_min": 1.1},
            {"from": "start", "to": "b202", "distance_km": 0.70, "duration_min": 2.3},
            {"from": "a101", "to": "b202", "distance_km": 0.65, "duration_min": 2.0},
            {"from": "b202", "to": "g707", "distance_km": 1.10, "duration_min": 3.4},
            {"from": "g707", "to": "d404", "distance_km": 0.95, "duration_min": 3.0},
            {"from": "d404", "to": "f606", "distance_km": 1.25, "duration_min": 4.0},
        ],
        "units": {"distance": "km", "duration": "min"},
        "note": "Pairs are sparse in this unit test; OK as long as validate_plan accepts it."
    }

    # ----------------------------
    # Mock the tools registry calls
    # ----------------------------
    class _Spec:
        def __init__(self, fn, arg_types=None):
            self.fn = fn
            self.arg_types = arg_types or {}

    def fake_get_tool_spec(name: str):
        if name == "get_nearby_stations":
            return _Spec(fn=lambda **kwargs: fake_stations, arg_types={})
        if name == "get_distances":
            return _Spec(fn=lambda **kwargs: fake_distances, arg_types={})
        raise KeyError(f"Unknown tool: {name}")

    monkeypatch.setattr(orch_mod, "get_tool_spec", fake_get_tool_spec)

    # If your coerce/validate are strict, you can keep them, but this makes the test robust:
    monkeypatch.setattr(orch_mod, "coerce_args", lambda raw_args, arg_types: raw_args)
    monkeypatch.setattr(orch_mod, "validate_args_against_signature", lambda fn, args: None)

    # ----------------------------
    # Mock validate_plan so we only test the loop + final formatting
    # ----------------------------
    monkeypatch.setattr(orch_mod, "validate_plan", lambda plan, ctx: [])

    # ----------------------------
    # Mock LLM: deterministic multi-step protocol
    # ----------------------------
    llm_messages = [
        # Step 1: Request nearby stations (different coords + radius than your ICL)
        """
        {
          "type": "TOOL_REQUEST",
          "tool": "get_nearby_stations",
          "args": {
            "k": 8,
            "radius_km": 1.6,
            "lat": 39.5648,
            "lon": 2.6549
          }
        }
        """.strip(),

        # Step 2: Request distances using stations (orchestrator will provide stations in context)
        """
        {
          "type": "TOOL_REQUEST",
          "tool": "get_distances",
          "args": {
            "stations": [
              {"id": "a101", "latitude": 39.56310, "longitude": 2.65340},
              {"id": "b202", "latitude": 39.56590, "longitude": 2.65810},
              {"id": "c303", "latitude": 39.56180, "longitude": 2.64890},
              {"id": "d404", "latitude": 39.56840, "longitude": 2.65120},
              {"id": "e505", "latitude": 39.56990, "longitude": 2.65760},
              {"id": "f606", "latitude": 39.56070, "longitude": 2.65600},
              {"id": "g707", "latitude": 39.56630, "longitude": 2.64650},
              {"id": "h808", "latitude": 39.57110, "longitude": 2.65280}
            ],
            "start_coordinates": {"lat": 39.5648, "lon": 2.6549}
          }
        }
        """.strip(),

        # Step 3: Plan (different ordering + actions; not your ICL plan)
        """
        {
          "type": "PLAN",
          "assumptions": {
            "truck_capacity": 10,
            "time_budget_min": 55
          },
          "stops": [
            {"station_id": "b202", "action": "pickup",  "bikes": 6},
            {"station_id": "f606", "action": "pickup",  "bikes": 4},

            {"station_id": "g707", "action": "dropoff", "bikes": 7},
            {"station_id": "a101", "action": "dropoff", "bikes": 3}
          ]
        }
        """.strip(),
    ]

    def fake_call_llm(llm_input):
        # Pop in order to emulate steps
        if not llm_messages:
            raise AssertionError("LLM was called more times than expected.")
        return llm_messages.pop(0)

    monkeypatch.setattr(orch_mod, "call_llm", fake_call_llm)

    # ----------------------------
    # Run orchestrator
    # ----------------------------
    payload = {
        "user_request": "Plan a short rebalancing route and keep it under 1 hour.",
        "start_coordinates": {"lat": 39.5648, "lon": 2.6549},
    }

    result_text = orch_mod.orchestrator(payload)

    # ----------------------------
    # Assertions: final formatted output contains expected content
    # ----------------------------
    assert "Citybike Rebalancing Route" in result_text
    assert "Start location" in result_text

    # Station short IDs should appear (first 4 chars)
    assert "Station b202" in result_text
    assert "Station f606" in result_text
    assert "Station g707" in result_text
    assert "Station a101" in result_text

    # Ensure both pickup and dropoff are present
    assert "Pick up" in result_text
    assert "Drop off" in result_text
