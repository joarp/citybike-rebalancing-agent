from pathlib import Path
from dotenv import load_dotenv

# ------------------------------------------------------------------
# Load .env from project root
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

from bike_agent.tools.get_distances import get_distances


def test_get_distances():
    # Reasonable, small set of nearby stations in Palma
    stations = [
        {"id": "a1", "latitude": 39.569083, "longitude": 2.650667},
        {"id": "b2", "latitude": 39.571465, "longitude": 2.648662},
        {"id": "c3", "latitude": 39.568611, "longitude": 2.646278},
        {"id": "d4", "latitude": 39.570278, "longitude": 2.655833},
    ]

    start_coordinates = {"lat": 39.5696, "lon": 2.6502}

    result = get_distances(
        stations=stations,
        start_coordinates=start_coordinates,
        # base_url NOT set → uses OSRM_BASE_URL from .env or default
        # profile left as default ("driving")
    )

    print("\n=== get_distances OUTPUT ===")
    print(result)


# -------------------------------
# RUN TEST
# -------------------------------
if __name__ == "__main__":
    test_get_distances()
