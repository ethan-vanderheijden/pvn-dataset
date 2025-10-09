#!/usr/bin/env python3

import asyncio
import aiohttp
import argparse
import time

parser = argparse.ArgumentParser(
    description="Drives RDR parent cache desired rate."
)
parser.add_argument("client_cache", type=str, help="Address of RDR Client Cache")
parser.add_argument("dest_url", type=str, help="URL to make get requests to")
parser.add_argument("interval", type=int, help="Time between consecutive HTTP requests")
args = parser.parse_args()


_tasks = set()


def spawn_task(coro):
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def make_conn(session):
    async with session.get(args.dest_url, proxy=f"http://{args.client_cache}", verify_ssl=False) as response:
        await response.read()


async def main():
    start = time.time()
    count = 0
    drift = 0
    async with aiohttp.ClientSession(auto_decompress=False) as session:
        while True:
            spawn_task(make_conn(session))

            drift = time.time() - (start + args.interval * count)
            await asyncio.sleep(args.interval - drift)
            count += 1


asyncio.run(main())
