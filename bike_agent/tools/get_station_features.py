# get_station_features.py
import os
import pandas as pd
from .feature_store import get_features

def get_station_features(station_ids, fields):
    """
    Fetch specified fields for given station IDs from the feature store.
    """
    df = get_features(api_key=os.getenv("HOPSWORKS_API_KEY"))
    latest_idx = df.groupby("id")["timestamp"].idxmax()
    latest = df.loc[latest_idx].copy()

    # Filter for requested station IDs
    filtered = latest[latest["id"].isin(station_ids)]

    # Ensure all requested fields exist
    missing_fields = set(fields) - set(filtered.columns)
    if missing_fields:
        raise ValueError(f"Missing fields in feature store: {missing_fields}")

    return filtered[["id"] + fields].reset_index(drop=True)
