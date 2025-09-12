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


async def main():
    print("handshake_duration")
    while True:
        try:
            start = time.time()
            _, writer = await asyncio.open_connection(args.server, 443)
            await writer.start_tls(
                ssl_context, ssl_handshake_timeout=5, ssl_shutdown_timeout=5, server_hostname=args.server
            )
            writer.close()
            await writer.wait_closed()
            end = time.time()
            print(f"{(end - start) * 1000:.3f}")
        except Exception as e:
            print(f"Error connecting to {args.server}: {e}", file=sys.stderr)


asyncio.run(main())
