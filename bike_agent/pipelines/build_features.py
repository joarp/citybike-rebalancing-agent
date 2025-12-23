# build features and upload to hopsworks (run this hourly)
# temporary script that can be run on demand until we decide on exact structure

import requests
import pandas as pd
import hopsworks
import datetime
import json
import os
from dotenv import load_dotenv

def main():
    network_id = "bicipalma"
    url = f"https://api.citybik.es/v2/networks/{network_id}"
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Station Count: {len(response.json()['network']['stations'])}")
    data = response.json()

    stations = data["network"]["stations"]
    df = pd.DataFrame(stations)
    df["timestamp"] = (df["timestamp"].str.replace("Z", "", regex=False).pipe(pd.to_datetime, utc=True))
    df.drop(columns=["extra"], inplace=True)

    # Load variables from .env (keep it in the same folder for now, will fix when running the finished app later)
    load_dotenv()

    # Connect to Hopsworks using the .env variables
    project = hopsworks.login(api_key_value=os.getenv("HOPSWORKS_API_KEY"))
    print(f"Connected to MJ Project: {project.name}")

    # Create feature group
    fs = project.get_feature_store()
    bike_fg = fs.get_or_create_feature_group(
        name="station_dynamics",
        version=1,
        primary_key=['id'],
        event_time='timestamp',
        online_enabled=True,
    )
    bike_fg.insert(df)

    # Register the Feature View
    query = bike_fg.select_all()
    feature_view = fs.get_or_create_feature_view(
        name="station_dynamics_view",
        version=1,
        description="Interface for Rebalancing Agent to get station state and history",
        query=query
    )

    print(f"Feature View '{feature_view.name}' version {feature_view.version} is ready!")

if __name__=="__main__":
    main()