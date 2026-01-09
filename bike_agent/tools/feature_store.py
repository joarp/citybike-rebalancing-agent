import hopsworks
import os

def get_features(api_key):
    project = hopsworks.login(api_key_value=api_key)
    fs = project.get_feature_store()
    
    # Try to get the view first for speed, fallback to group
    try:
        fv = fs.get_feature_view(name="station_dynamics_view", version=1)
        return fv.get_batch_data()
    except:
        fg = fs.get_feature_group(name="station_dynamics", version=1)
        return fg.read()