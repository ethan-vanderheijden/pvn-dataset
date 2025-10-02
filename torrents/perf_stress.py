#!/usr/bin/env python3

import argparse
import requests
import sys
import time

parser = argparse.ArgumentParser(description="Drives torrent client at constant rate and measures performance.")
parser.add_argument("--bps", type=int, default=None, help="Download limit in bytes per second")
parser.add_argument("client_address", type=str, help="Path to the torrent client executable")
parser.add_argument("torrent_file", type=str, help="Path to the torrent file")

args = parser.parse_args()

api_url = f"http://{args.client_address}"

upload_response = requests.post(
    f"{api_url}/torrent_files",
    files={"torrent_file": open(args.torrent_file, "rb")},
)
upload_response.raise_for_status()

torrent_file_id = upload_response.text

while True:
    start = time.time()
    start_response = requests.post(
        f"{api_url}/torrents",
        json={
            "file": torrent_file_id,
            "download_bps": args.bps,
        },
    )
    start_response.raise_for_status()

    torrent_id = start_response.json()["id"]

    while True:
        time.sleep(1)

        status_response = requests.get(f"{api_url}/torrents/{torrent_id}")
        status_response.raise_for_status()

        status = status_response.json()
        if status["stats"]["finished"]:
            download_response = requests.get(
                f"{api_url}/torrents/{torrent_id}/download",
                stream=True,
            )
            download_response.raise_for_status()
            for chunk in download_response.iter_content(chunk_size=8192):
                pass

            end = time.time()
            print(f"Download completed in {end - start:.2f} seconds")

            delete_request = requests.delete(f"{api_url}/torrents/{torrent_id}")
            delete_request.raise_for_status()

            break
        else:
            time_remaining = status["stats"]["live"]["time_remaining"]
            if time_remaining is not None:
                time_remaining = time_remaining["human_readable"]
            else:
                time_remaining = "0s"
            print(f"Time left: {time_remaining}", file=sys.stderr)
