#!/usr/bin/env python3

import argparse
import requests
import random
import time
import pandas as pd
import xml.etree.ElementTree as ET
import sys

parser = argparse.ArgumentParser(
    description="Drives video transcoder at maximum rate and measures performance."
)
parser.add_argument("proxy_address", type=str, help="Address of the transcoding proxy")
parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
parser.add_argument(
    "--representation-bw",
    type=int,
    default=None,
    help="Specific representation bandwidth to request, otherwise it loads a random representation",
)
args = parser.parse_args()

proxies = {"http": f"http://{args.proxy_address}"}
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
        print(f"Error fetching data from {endpoint}: {e}", file=sys.stderr)
        return None


random.seed(args.seed)
endpoint = endpoints.sample(1, random_state=args.seed).iloc[0]
print(f"Selected endpoint: {endpoint}", file=sys.stderr)
dash_url = extract_dash_url(endpoint)
print(f"DASH URL: {dash_url if dash_url else 'No DASH URL found'}\n", file=sys.stderr)

if dash_url:
    dash = requests.get(dash_url, proxies=proxies).text
    root = ET.fromstring(dash)
    period = root.find("{urn:mpeg:dash:schema:mpd:2011}Period")
    target_representation = None
    if period is not None:
        for sets in period.findall("{urn:mpeg:dash:schema:mpd:2011}AdaptationSet"):
            if sets.get("contentType") == "video":
                representations = sets.findall("{urn:mpeg:dash:schema:mpd:2011}Representation")
                print(
                    f"Possible representations: {[rep.get('bandwidth') for rep in representations]}",
                    file=sys.stderr,
                )
                if args.representation_bw:
                    for rep in representations:
                        if rep.get("bandwidth") == str(args.representation_bw):
                            target_representation = rep
                            break
                else:
                    target_representation = random.choice(representations)

    if target_representation is not None:
        segment_template = target_representation.find(
            "{urn:mpeg:dash:schema:mpd:2011}SegmentTemplate"
        )
        if segment_template is not None:
            repr_id = target_representation.get("id")
            init = segment_template.get("initialization").replace("$RepresentationID$", repr_id)
            media = (
                segment_template.get("media")
                .replace("$RepresentationID$", repr_id)
                .replace("$Number$", "3")
            )
            base_url = dash_url.rsplit("/", 1)[0] + "/dash/"

            init_url = base_url + init
            media_url = base_url + media
            print(f"Initialization URL: {init_url}", file=sys.stderr)
            print(f"Media URL: {media_url}", file=sys.stderr)

            requests.get(init_url, proxies=proxies)
            print("time,transcode_duration")
            offset = time.time()
            while True:
                start = time.time()
                response = requests.get(media_url, proxies=proxies)
                if response.status_code != 200:
                    print(f"Error fetching media segment: {response.status_code}", file=sys.stderr)
                    continue
                end = time.time()
                duration = end - start
                print(f"{(end - offset):.4f},{duration:.4f}")
    else:
        print("No suitable representation found.", file=sys.stderr)
        exit(1)
