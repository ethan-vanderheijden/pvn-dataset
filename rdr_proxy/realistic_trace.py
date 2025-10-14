#!/usr/bin/env python3

import argparse
import aiohttp
import asyncio
import random
import time
import pandas as pd

parser = argparse.ArgumentParser(description="Simulates a realistic web browsing workload.")
parser.add_argument("proxy", type=str, help="Proxy server address to send requests through")
args = parser.parse_args()

_tasks = set()


def spawn_task(coro):
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def visit_page(session, url):
    async with session.get(url, proxy=f"http://{args.proxy}", verify_ssl=False) as response:
        print(f"Fetched {url} with status {response.status}")
        await response.read()


async def main():
    async with aiohttp.ClientSession(auto_decompress=False) as session:
        start = time.time()
        for _, row in trace.iterrows():
            target = start + row["used_at"]
            diff = target - time.time()
            if diff > 0:
                print("Sleeping for", diff)
                await asyncio.sleep(diff)

            print("Visiting", row["page"])
            spawn_task(visit_page(session, row["page"]))


if __name__ == "__main__":
    data = pd.read_csv("output/traces.csv")
    trace_id = random.choices(data["trace"].unique())
    trace = data[data["trace"] == trace_id[0]].sort_values("used_at")

    print("Simulating trace:", trace_id[0])

    asyncio.run(main())
