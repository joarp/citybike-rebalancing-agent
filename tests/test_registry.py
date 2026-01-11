from pathlib import Path
from dotenv import load_dotenv

# Optional: keep consistent with your other tests (registry itself doesn't need env)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

from bike_agent.tools.registry import list_tools, get_tool_spec, get_tool


def test_registry():
    print("\n=== REGISTERED TOOLS ===")
    print(list_tools())

    # Print one spec to confirm it exists and is wired
    name = "get_distances"
    spec = get_tool_spec(name)
    print(f"\n=== SPEC: {name} ===")
    print("fn:", spec.fn)
    print("arg_types:", spec.arg_types)
    print("description:", spec.description)

    # Also test get_tool
    fn = get_tool("get_nearby_stations")
    print("\n=== get_tool('get_nearby_stations') ===")
    print(fn)


# -------------------------------
# RUN TEST
# -------------------------------
if __name__ == "__main__":
    test_registry()
