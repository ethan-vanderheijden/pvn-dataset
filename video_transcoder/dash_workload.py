#!/usr/bin/env python3

import sys
import requests
import pandas as pd
import subprocess

endpoints = pd.read_csv("bbc_dash.csv", comment="#")["bbc_videos"]


def extract_dash_url(endpoint):
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        data = response.json()

        for media in data.get("media", []):
            if media.get("kind") == "video":
                for connection in media.get("connection", []):
                    if (
                        connection.get("protocol") == "http"
                        and connection.get("transferFormat") == "dash"
                    ):
                        return connection.get("href")
        return None
    except Exception as e:
        print(f"Error fetching data from {endpoint}: {e}")
        return None


endpoint = endpoints.sample(1).iloc[0]
print(f"Selected endpoint: {endpoint}")
dash_url = extract_dash_url(endpoint)
print(f"DASH URL: {dash_url if dash_url else 'No DASH URL found'}")

subprocess.run(
    ["xvfb-run", "dbus-run-session", "cvlc", "--no-audio", dash_url],
    env={"http_proxy": "http://" + sys.argv[1]},
)
