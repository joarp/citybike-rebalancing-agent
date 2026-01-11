# bike_agent/tools/get_distances.py
import os
from typing import Dict, List, Union, Optional

import numpy as np
import pandas as pd
import requests


def get_distances(
    stations: Union[pd.DataFrame, List[Dict]],
    start_coordinates: Optional[Dict[str, float]] = None,
    base_url: str = None,
    profile: str = "driving",
) -> Dict:
    """
    Compute pairwise driving distance + driving time between candidate stations using OSRM table.

    RETURNS (compact, readable, triangular/unique pairs):
    {
      "ids": [id0, id1, ...],   # ordering used internally (start is prepended if added)
      "pairs": [
         {"from": id_i, "to": id_j, "distance_km": <float>, "duration_min": <float>},
         ... for all i<j
      ],
      "units": {"distance": "km", "duration": "min"}
    }

    Note: This is an UNDIRECTED approximation for readability.
    We take the average of OSRM(i->j) and OSRM(j->i) for distance/time.
    """
    if base_url is None:
        base_url = os.getenv("OSRM_BASE_URL", "http://router.project-osrm.org")

    # Normalize input to DataFrame
    if isinstance(stations, list):
        df = pd.DataFrame(stations)
    elif isinstance(stations, pd.DataFrame):
        df = stations.copy()
    else:
        raise TypeError("stations must be a pd.DataFrame or list[dict].")

    required = {"id", "latitude", "longitude"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"stations is missing required columns: {sorted(missing)}")

    df["id"] = df["id"].astype(str)

    # Optionally inject "start"
    if start_coordinates is not None:
        if not isinstance(start_coordinates, dict) or "lat" not in start_coordinates or "lon" not in start_coordinates:
            raise ValueError("start_coordinates must be a dict with keys {'lat','lon'}")

        has_start = (df["id"] == "start").any()
        if not has_start:
            start_row = pd.DataFrame([{
                "id": "start",
                "latitude": float(start_coordinates["lat"]),
                "longitude": float(start_coordinates["lon"]),
            }])
            df = pd.concat([start_row, df], ignore_index=True)

    if df.empty:
        return {"ids": [], "pairs": [], "units": {"distance": "km", "duration": "min"}}

    # Stable ordering
    ids = df["id"].tolist()

    # OSRM wants "lon,lat" pairs
    coords = ";".join([f"{lon},{lat}" for lon, lat in zip(df["longitude"], df["latitude"])])
    url = f"{base_url}/table/v1/{profile}/{coords}"
    params = {"annotations": "distance,duration"}

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    if data.get("code") != "Ok":
        raise RuntimeError(f"OSRM table failed: {data.get('code')}")

    dist_m = np.array(data["distances"], dtype=float)   # meters
    dur_s  = np.array(data["durations"], dtype=float)   # seconds

    # Build triangular unique pairs, using undirected approximation:
    # avg(i->j, j->i) to reduce directional noise and keep "one value per pair".
    n = len(ids)
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            dm_ij = dist_m[i, j]
            dm_ji = dist_m[j, i]
            ds_ij = dur_s[i, j]
            ds_ji = dur_s[j, i]

            # Average; if OSRM returns NaN for some reason, keep NaN (LLM can avoid those edges)
            dist_km = float(np.nanmean([dm_ij, dm_ji]) / 1000.0)
            dur_min  = float(np.nanmean([ds_ij, ds_ji]) / 60.0)

            pairs.append({
                "from": ids[i],
                "to": ids[j],
                "distance_km": dist_km,
                "duration_min": dur_min,
            })

    # For readability: sort by duration, so "closest" edges appear first
    pairs.sort(key=lambda x: (x["duration_min"], x["distance_km"]))

    return {
        "ids": ids,
        "pairs": pairs,
        "units": {"distance": "km", "duration": "min"},
        "note": "pairs are undirected approx: avg(i->j, j->i). Use full matrix if you need directionality.",
    }