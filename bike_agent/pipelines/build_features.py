# bike_agent/pipelines/build_features.py

import os
import requests
import pandas as pd
import hopsworks

def main():
    network_id = "bicipalma"
    url = f"https://api.citybik.es/v2/networks/{network_id}"

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    stations = data["network"]["stations"]
    df = pd.DataFrame(stations)

    df["timestamp"] = (
        df["timestamp"]
        .str.replace("Z", "", regex=False)
        .pipe(pd.to_datetime, utc=True)
    )
    if "extra" in df.columns:
        df.drop(columns=["extra"], inplace=True)

    api_key = os.getenv("HOPSWORKS_API_KEY")
    if not api_key:
        raise RuntimeError("HOPSWORKS_API_KEY is not set (use GitHub Secrets in Actions).")

    project = hopsworks.login(api_key_value=api_key)
    print(f"Connected to Hopsworks project: {project.name}")

    fs = project.get_feature_store()
    bike_fg = fs.get_or_create_feature_group(
        name="station_dynamics",
        version=1,
        primary_key=["id"],
        event_time="timestamp",
        online_enabled=True,
    )
    bike_fg.insert(df)

    query = bike_fg.select_all()
    feature_view = fs.get_or_create_feature_view(
        name="station_dynamics_view",
        version=1,
        description="Interface for Rebalancing Agent to get station state and history",
        query=query,
    )

    print(f"Feature View '{feature_view.name}' version {feature_view.version} is ready!")

if __name__ == "__main__":
    main()