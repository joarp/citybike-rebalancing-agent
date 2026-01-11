import os
import numpy as np
import pandas as pd
from .feature_store import get_features

"""
Computes distance from the current driver location (START_LAT, START_LON) to each station.

Filters stations by radius and k nearest.

Returns a small subset of stations near the driver with distances.

Use case: “I'm at this spot — which stations are close enough to visit next?”

So get_nearby_stations is driver-centric and gives a local, filtered view.
"""

def _haversine_km(lat1, lon1, lat2, lon2):
    """
    Compute Haversine distance in km between two points.
    Works with floats, lists, or Pandas Series/NumPy arrays.
    """
    # Convert everything to NumPy arrays
    lat1 = np.asarray(lat1, dtype=float)
    lon1 = np.asarray(lon1, dtype=float)
    lat2 = np.asarray(lat2, dtype=float)
    lon2 = np.asarray(lon2, dtype=float)

    # Convert to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    R = 6371  # Earth radius in km
    return R * c

def get_nearby_stations(k: int, radius_km: float, lat: float, lon: float) -> pd.DataFrame:
    """
    Returns nearby station IDs, coordinates, free_bikes, empty_slots in order of how close they are.

    Output columns:
      id, latitude, longitude, free_bikes, empty_slots, distance_km
    """
    if k <= 0:
        raise ValueError("k must be a positive integer.")
    if radius_km <= 0:
        raise ValueError("radius_km must be > 0.")

    df = get_features(api_key=os.getenv("HOPSWORKS_API_KEY"))

    required = {"id", "latitude", "longitude", "timestamp", "free_bikes", "empty_slots"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"get_features() is missing required columns: {sorted(missing)}")

    # Take latest observation per station id
    latest_idx = df.groupby("id")["timestamp"].idxmax()
    latest = df.loc[latest_idx].copy()

    # Compute distance and filter by radius
    latest["distance_km"] = _haversine_km(
        lat, lon,
        latest["latitude"], latest["longitude"]
    )

    nearby = latest[latest["distance_km"] <= float(radius_km)].copy()
    nearby = nearby.sort_values("distance_km", ascending=True).head(int(k))

    # Return requested fields (plus distance_km which is useful)
    return nearby[["id", "latitude", "longitude", "free_bikes", "empty_slots", "distance_km"]].reset_index(drop=True)