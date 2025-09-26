#!/usr/bin/env python3

import asyncio
import argparse
import time
import ssl
import sys

parser = argparse.ArgumentParser(
    description="Drives TLS validator at maximum rate and measures performance."
)
parser.add_argument("server", type=str, help="Address of target TLS server")
args = parser.parse_args()

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

REPORT_INTERVAL = 5
NUM_THREADS = 10

num_handshakes = 0


async def report_data():
    global num_handshakes
    print("time,handshakes_completed")
    start = time.time()
    last = 0
    drift = 0
    count = 0
    while True:
        await asyncio.sleep(REPORT_INTERVAL - drift)
        curr = time.time()
        count += 1
        drift = curr - (start + REPORT_INTERVAL * count)
        print(f"{(curr - start):.4f},{num_handshakes - last}")
        last = num_handshakes


async def spam_connections():
    global num_handshakes
    while True:
        try:
            _, writer = await asyncio.open_connection(args.server, 443)
            await writer.start_tls(
                ssl_context, ssl_handshake_timeout=5, ssl_shutdown_timeout=5, server_hostname=args.server
            )
            writer.close()
            await writer.wait_closed()
            num_handshakes += 1
        except Exception as e:
            print(f"Error connecting to {args.server}: {e}", file=sys.stderr)


async def main():
    global num_handshakes
    asyncio.create_task(report_data())
    await asyncio.gather(*[spam_connections() for i in range(0, NUM_THREADS)])


asyncio.run(main())
