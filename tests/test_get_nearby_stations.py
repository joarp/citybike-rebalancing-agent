from bike_agent.tools.get_nearby_stations import get_nearby_stations
from pathlib import Path
from dotenv import load_dotenv

# ------------------------------------------------------------------
# Load .env from project root
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

def test_get_nearby_stations():
    print(get_nearby_stations(8, 2.0, 39.5696, 2.6502))

# -------------------------------
# RUN TEST
# -------------------------------
if __name__ == "__main__":
    test_get_nearby_stations()