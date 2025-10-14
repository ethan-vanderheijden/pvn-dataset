#!/usr/bin/env python3

import sys
import requests
import random
import time
import pandas as pd
import subprocess

if len(sys.argv) != 2:
    print("Usage: python3 dash_workload.py <proxy_address>")
    sys.exit(1)

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


while True:
    endpoint = endpoints.sample(1).iloc[0]
    print(f"Selected endpoint: {endpoint}")
    dash_url = extract_dash_url(endpoint)
    print(f"DASH URL: {dash_url if dash_url else 'No DASH URL found'}")

    # random runtime up to 0.5 to 5 minutes
    runtime = random.randint(30, 300)
    print(f"Running for up to {runtime} seconds")

    process = subprocess.Popen(
        ["xvfb-run", "dbus-run-session", "cvlc", "--no-audio", dash_url],
        env={"http_proxy": "http://" + sys.argv[1]},
    )

    process.wait(timeout=runtime)

    sleep_time = random.randint(45, 120)
    print(f"Sleeping for {sleep_time} seconds before next video")
    time.sleep(sleep_time)
