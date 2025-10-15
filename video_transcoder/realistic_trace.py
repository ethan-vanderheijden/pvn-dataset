#!/usr/bin/env python3

import argparse
import requests
import random
import time
import psutil
import os
import signal
import pandas as pd
import subprocess

MIN_SLEEP_TIME = 30
MAX_SLEEP_TIME = 180
MIN_PLAY_TIME = 30
MAX_PLAY_TIME = 90
MIN_PAUSE_TIME = 10
MAX_PAUSE_TIME = 45

parser = argparse.ArgumentParser(description="Drives video transcoder with real DASH videos and random pauses.")
parser.add_argument("proxy_address", type=str, help="Address of the HTTP proxy to use")
args = parser.parse_args()

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

    process = subprocess.Popen(
        ["xvfb-run", "dbus-run-session", "cvlc", "--no-audio", dash_url],
        env={"http_proxy": "http://" + args.proxy_address},
    )

    time_until_pause = random.randint(MIN_PAUSE_TIME, MAX_PAUSE_TIME)
    print(f"Playing video for up to {time_until_pause} seconds")

    # give VLC some time to start
    time.sleep(5)
    time_until_pause -= 5

    vlc_pid = None
    for child in psutil.Process(process.pid).children(recursive=True):
        executable = child.exe()
        if executable.split("/")[-1] == "vlc":
            vlc_pid = child.pid
            print(f"VLC PID: {vlc_pid}")

    if vlc_pid is None:
        print("VLC process not found, terminating.")
        process.terminate()
        process.wait()
        break

    while process.poll() is None:
        if time_until_pause <= 0:
            os.kill(vlc_pid, signal.SIGSTOP)
            pause_time = random.randint(MIN_PAUSE_TIME, MAX_PAUSE_TIME)
            print(f"Pausing video for {pause_time} seconds")
            time.sleep(pause_time)
            os.kill(vlc_pid, signal.SIGCONT)
            time_until_pause = random.randint(MIN_PAUSE_TIME, MAX_PAUSE_TIME)
            print(f"Resuming video for up to {time_until_pause} seconds")
        else:
            time_until_pause -= 1
            time.sleep(1)

    sleep_time = random.randint(MIN_SLEEP_TIME, MAX_SLEEP_TIME)
    print(f"Waiting {sleep_time} seconds before next video")
    time.sleep(sleep_time)
