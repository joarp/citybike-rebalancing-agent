# bike_agent/tools/get_distances.py
import os
import numpy as np
import pandas as pd

from .feature_store import get_features
from .get_nearby_stations import _haversine_km


def get_distances(station_ids) -> pd.DataFrame:
    """
    Compute pairwise distances (km) between a list of stations.

    Args:
        station_ids: List[str]
            Example: ["id1", "id2", "id3"]

    Returns:
        pd.DataFrame:
            Square distance matrix in km with index=station_ids and columns=station_ids.
            dist.loc[a, b] = distance_km(a -> b). Diagonal is 0.

    Notes:
        - Uses latest observation per station from feature store for coordinates.
        - Raises if any requested station_id is missing.
    """
    if not isinstance(station_ids, (list, tuple)) or len(station_ids) == 0:
        raise ValueError("station_ids must be a non-empty list/tuple of station IDs.")

    # Ensure string IDs and stable order
    ids = [str(x) for x in station_ids]

    df = get_features(api_key=os.getenv("HOPSWORKS_API_KEY"))

    required = {"id", "latitude", "longitude", "timestamp"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"get_features() is missing required columns: {sorted(missing)}")

    # Take latest observation per station id (same pattern as get_nearby_stations)
    latest_idx = df.groupby("id")["timestamp"].idxmax()
    latest = df.loc[latest_idx, ["id", "latitude", "longitude"]].copy()

    # Filter to requested stations
    subset = latest[latest["id"].isin(ids)].copy()

    # Check for missing station IDs
    found = set(subset["id"].astype(str))
    missing_ids = [sid for sid in ids if sid not in found]
    if missing_ids:
        raise ValueError(f"Requested station_ids not found in latest features: {missing_ids}")

    # Reorder subset to match input order
    subset["_order"] = subset["id"].map({sid: i for i, sid in enumerate(ids)})
    subset = subset.sort_values("_order").drop(columns="_order")

    lats = subset["latitude"].to_numpy(dtype=float)
    lons = subset["longitude"].to_numpy(dtype=float)

    n = len(ids)
    matrix = np.zeros((n, n), dtype=float)

    # Compute distances (vectorized row-by-row)
    for i in range(n):
        matrix[i, :] = _haversine_km(lats[i], lons[i], lats, lons)

    return pd.DataFrame(matrix, index=ids, columns=ids)
