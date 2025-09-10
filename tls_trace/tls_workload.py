#!/usr/bin/env python3

import asyncio
import pandas as pd
import random
import time
import ssl
import sys

data = pd.read_csv("output/combined.csv")
trace_id = random.choice(data["trace"].unique())
traces = data[data["trace"] == trace_id]

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

_tasks = set()


def spawn_task(coro):
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def tls_connect(domain):
    start = time.time()
    print("Visiting", domain)
    try:
        _, writer = await asyncio.open_connection(domain, 443)
        await writer.start_tls(
            ssl_context, ssl_handshake_timeout=5, ssl_shutdown_timeout=5, server_hostname=domain
        )
        writer.close()
        await writer.wait_closed()
        end = time.time()
        print(f"Connected to {domain} in {(end - start) * 1000} ms")
    except Exception as e:
        print(f"Error connecting to {domain}: {e}")


async def main(override_domains=None):
    start = time.time()
    for _, row in traces.iterrows():
        diff = row["timestamp"] - (time.time() - start)
        if diff > 0:
            print("Sleeping for", diff)
            await asyncio.sleep(diff)
        domain = row["url"]
        if override_domains:
            domain = random.choice(override_domains)
        spawn_task(tls_connect(domain))


override_domains = sys.argv[1:] if len(sys.argv) > 1 else None
asyncio.run(main(override_domains))
