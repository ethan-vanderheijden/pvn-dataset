#!/usr/bin/env python3

import argparse
import aiohttp
import asyncio
import random
import time
import pandas as pd

parser = argparse.ArgumentParser(description="Simulates a realistic web browsing workload.")
parser.add_argument("proxy", type=str, help="Proxy server address to send requests through")
parser.add_argument("--traces", type=int, default=1, help="Number of traces to simulate simultaneously")
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
    trace_ids = random.choices(data["trace"].unique(), k=args.traces)
    trace = data[data["trace"].isin(trace_ids)].sort_values("used_at")

    print(f"Simulating {args.traces} traces with total {len(trace)} requests")

    asyncio.run(main())
