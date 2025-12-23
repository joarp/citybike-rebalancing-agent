import os
import numpy as np
import pandas as pd

from feature_store import get_features

# Temporary global variables that will be set by the driver (his coordinates)
START_LAT = 39.566056
START_LON = 2.659389

def _haversine_km(lat1, lon1, lat2, lon2):
    """
    Vectorized Haversine distance (km). lat2/lon2 can be numpy arrays/Series.
    """
    R = 6371.0  # Earth radius in km

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2.astype(float))
    lon2 = np.radians(lon2.astype(float))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return R * c


def get_nearby_stations(k: int, radius_km: float) -> pd.DataFrame:
    """
    Returns nearby station IDs, coordinates, free_bikes, empty_slots in order of how close they are.

    Driver coordinates are taken from temporary global vars:
      - START_LAT
      - START_LON

    Output columns:
      id, latitude, longitude, free_bikes, empty_slots, distance_km
    """
    if k <= 0:
        raise ValueError("k must be a positive integer.")
    if radius_km <= 0:
        raise ValueError("radius_km must be > 0.")

    lat_str = START_LAT
    lon_str = START_LON

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
        lat_str, lon_str,
        latest["latitude"], latest["longitude"]
    )

    nearby = latest[latest["distance_km"] <= float(radius_km)].copy()
    nearby = nearby.sort_values("distance_km", ascending=True).head(int(k))

    # Return requested fields (plus distance_km which is useful)
    return nearby[["id", "latitude", "longitude", "free_bikes", "empty_slots", "distance_km"]].reset_index(drop=True)
