# read from feature store (query Hopsworks)
import hopsworks
import pandas as pd

def get_features(api_key, fg_name = "station_dynamics", fg_version = 1):
    project = hopsworks.login(project=api_key)
    fs = project.get_feature_store()
    fg = fs.get_feature_group(name=fg_name, version=fg_version)
    df = fg.read()
    return df