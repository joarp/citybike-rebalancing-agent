# # read from feature store (query Hopsworks)
# import hopsworks
# import pandas as pd

# def get_features(api_key, fg_name = "station_dynamics", fg_version = 1):
#     project = hopsworks.login(project=api_key)
#     fs = project.get_feature_store()
#     fg = fs.get_feature_group(name=fg_name, version=fg_version)
#     df = fg.read()
#     return df



import hopsworks
import os

def get_features(api_key):
    # Logging in without a hardcoded name finds the project linked to the key
    project = hopsworks.login(api_key_value=api_key)
    fs = project.get_feature_store()
    
    # Try to get the view first for speed, fallback to group
    try:
        fv = fs.get_feature_view(name="station_dynamics_view", version=1)
        return fv.get_batch_data()
    except:
        fg = fs.get_feature_group(name="station_dynamics", version=1)
        return fg.read()