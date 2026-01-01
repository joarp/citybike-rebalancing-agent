# get_distances.py
import numpy as np
import pandas as pd
from .get_nearby_stations import _haversine_km
from .feature_store import get_features
import os

def get_distances(stations_df):
    """
    stations_df: DataFrame with columns ['lat', 'lon'], index = station id (including 'start')
    Returns: distance matrix (DataFrame)
    """
    import numpy as np
    import pandas as pd
    from .get_nearby_stations import _haversine_km

    ids = stations_df.index.tolist()
    n = len(ids)
    matrix = np.zeros((n, n))

    for i, id1 in enumerate(ids):
        lat1, lon1 = stations_df.loc[id1, ["lat", "lon"]]
        for j, id2 in enumerate(ids):
            lat2, lon2 = stations_df.loc[id2, ["lat", "lon"]]
            matrix[i, j] = _haversine_km(lat1, lon1, lat2, lon2)

    return pd.DataFrame(matrix, index=ids, columns=ids)

