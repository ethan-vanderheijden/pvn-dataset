#!/usr/bin/env python3

import argparse
import psutil
import time
import sys

parser = argparse.ArgumentParser(
    description="Measures and reports system-wide and cgroup CPU utilization."
)
parser.add_argument(
    "-i", "--interval", type=int, default=500, help="Interval in milliseconds between measurements"
)
parser.add_argument("-c", "--cgroup", nargs="+", default=[], help="Cgroup paths to monitor")
args = parser.parse_args()

print("time,system,cpu,")

prev_cgroup_cpu_stats = {}
for cgroup_path in args.cgroup:
    prev_cgroup_cpu_stats[cgroup_path] = 0


def collect_cgroup_stat(cgroup_path):
    data = ""
    with open(f"/sys/fs/cgroup/{cgroup_path}/cpu.stat") as f:
        for line in f:
            key, value = line.split()
            if key == "usage_usec":
                usage = int(value)
                cpu_percent = (usage - prev_cgroup_cpu_stats[cgroup_path]) / 10 / args.interval
                prev_cgroup_cpu_stats[cgroup_path] = usage
                data += f"{cpu_percent},"
                break
        else:
            print(f"Failed to read CPU stats for '{cgroup_path}'", file=sys.stderr)
            return None

    return data


if __name__ == "__main__":
    start = time.time()
    psutil.cpu_percent(interval=None, percpu=True)

    for cgroup_path in args.cgroup:
        if collect_cgroup_stat(cgroup_path) is None:
            sys.exit(1)

    count = 1
    while True:
        now = time.time()
        time.sleep(count * args.interval / 1000 - (now - start))
        count += 1

        time_delta = int((time.time() - start) * 1000)
        data = f"{time_delta},systemwide,"

        cpu = sum(psutil.cpu_percent(interval=None, percpu=True))
        data += f"{cpu},"

        print(data)

        for cgroup_path in args.cgroup:
            cgroup_data = collect_cgroup_stat(cgroup_path)
            if cgroup_data is not None:
                print(f"{time_delta},{cgroup_path},{cgroup_data}")
