#!/usr/bin/env python3

import argparse
import psutil
import time
import sys
import os

parser = argparse.ArgumentParser(
    description="Measures and reports system-wide resource utilization."
)
parser.add_argument("disk", type=str, help="Disk device to monitor (e.g., sda1)")
parser.add_argument(
    "net_iface", type=str, help="Main outgoing network interface to monitor (e.g., enp1s0)"
)
parser.add_argument(
    "-i", "--interval", type=int, default=5, help="Interval in seconds between measurements"
)
parser.add_argument("-c", "--cgroup", nargs="+", default=[], help="Cgroup paths to monitor")
args = parser.parse_args()

major = os.major(os.stat(f"/dev/{args.disk}").st_rdev)
minor = os.minor(os.stat(f"/dev/{args.disk}").st_rdev)
disk_id = f"{major}:{minor}"

print(
    "time,"
    "system,"
    "cpu,"
    "mem_used,"
    "disk_r_ops_rate,disk_w_ops_rate,disk_r_bytes_rate,disk_w_bytes_rate,"
    "net_sent_pps,net_recv_pps,net_sent_bps,net_recv_bps"
)

prev_cgroup_cpu_stats = {}
prev_cgroup_io_stats = {}
prev_cgroup_net_stats = {}
for cgroup_path in args.cgroup:
    prev_cgroup_cpu_stats[cgroup_path] = 0
    prev_cgroup_io_stats[cgroup_path] = [0, 0, 0, 0]  # r_ops, w_ops, r_bytes, w_bytes
    # packets_sent, packets_recv, bytes_sent, bytes_recv
    prev_cgroup_net_stats[cgroup_path] = [0, 0, 0, 0]


def collect_cgroup_stat(cgroup_path):
    data = ""
    with open(f"/sys/fs/cgroup/{cgroup_path}/cpu.stat") as f:
        for line in f:
            key, value = line.split()
            if key == "usage_usec":
                usage = int(value)
                cpu_percent = (usage - prev_cgroup_cpu_stats[cgroup_path]) / 10000 / args.interval
                prev_cgroup_cpu_stats[cgroup_path] = usage
                data += f"{cpu_percent},"
                break
        else:
            print(f"Failed to read CPU stats for '{cgroup_path}'", file=sys.stderr)
            return None

    with open(f"/sys/fs/cgroup/{cgroup_path}/memory.current") as f:
        mem_used = int(f.read().strip())
        data += f"{mem_used},"

    with open(f"/sys/fs/cgroup/{cgroup_path}/io.stat") as f:
        for line in f:
            parts = line.split()
            r_bytes_rate, w_bytes_rate, r_ops_rate, w_ops_rate = None, None, None, None
            if parts[0] == disk_id:
                for part in parts[1:]:
                    key, value = part.split("=")
                    if key == "rios":
                        r_ops = int(value)
                        r_ops_rate = (r_ops - prev_cgroup_io_stats[cgroup_path][0]) / args.interval
                        prev_cgroup_io_stats[cgroup_path][0] = r_ops
                    elif key == "wios":
                        w_ops = int(value)
                        w_ops_rate = (w_ops - prev_cgroup_io_stats[cgroup_path][1]) / args.interval
                        prev_cgroup_io_stats[cgroup_path][1] = w_ops
                    elif key == "rbytes":
                        r_bytes = int(value)
                        r_bytes_rate = (
                            r_bytes - prev_cgroup_io_stats[cgroup_path][2]
                        ) / args.interval
                        prev_cgroup_io_stats[cgroup_path][2] = r_bytes
                    elif key == "wbytes":
                        w_bytes = int(value)
                        w_bytes_rate = (
                            w_bytes - prev_cgroup_io_stats[cgroup_path][3]
                        ) / args.interval
                        prev_cgroup_io_stats[cgroup_path][3] = w_bytes

            if (
                r_bytes_rate is not None
                and w_bytes_rate is not None
                and r_ops_rate is not None
                and w_ops_rate is not None
            ):
                data += f"{r_ops_rate},{w_ops_rate},{r_bytes_rate},{w_bytes_rate},"
                break
        else:
            print(f"Failed to read IO stats for '{cgroup_path}'", file=sys.stderr)
            return None

    with open(f"/sys/fs/cgroup/{cgroup_path}/cgroup.procs") as f:
        pid_str = f.readline().strip()
        if not pid_str:
            print(
                f"No processes in cgroup '{cgroup_path}', can't get network stats", file=sys.stderr
            )
            return None
        pid = int(pid_str)

    with open(f"/proc/{pid}/net/dev") as f:
        for line in f:
            parts = line.strip().split()
            if parts[0] == "eth0:":
                packets_recv = int(parts[2])
                bytes_recv = int(parts[1])
                packets_sent = int(parts[10])
                bytes_sent = int(parts[9])

                pps_sent = (packets_sent - prev_cgroup_net_stats[cgroup_path][0]) / args.interval
                pps_recv = (packets_recv - prev_cgroup_net_stats[cgroup_path][1]) / args.interval
                bps_sent = (bytes_sent - prev_cgroup_net_stats[cgroup_path][2]) / args.interval
                bps_recv = (bytes_recv - prev_cgroup_net_stats[cgroup_path][3]) / args.interval

                prev_cgroup_net_stats[cgroup_path] = [
                    packets_sent,
                    packets_recv,
                    bytes_sent,
                    bytes_recv,
                ]

                data += f"{pps_sent},{pps_recv},{bps_sent},{bps_recv}"
                break
        else:
            print(f"Failed to read network stats for '{cgroup_path}'", file=sys.stderr)
            return None

    return data


if __name__ == "__main__":
    start = time.time()
    psutil.cpu_percent(interval=None, percpu=True)
    prev_disk_io = psutil.disk_io_counters(perdisk=True)[args.disk]
    prev_net_io = psutil.net_io_counters(pernic=True)[args.net_iface]

    for cgroup_path in args.cgroup:
        if collect_cgroup_stat(cgroup_path) is None:
            sys.exit(1)

    count = 1
    while True:
        now = time.time()
        time.sleep(count * args.interval - (now - start))
        count += 1

        time_delta = int(now - start)
        data = f"{time_delta},systemwide,"

        cpu = sum(psutil.cpu_percent(interval=None, percpu=True))
        data += f"{cpu},"

        mem = psutil.virtual_memory()
        data += f"{mem.used},"

        disk_io = psutil.disk_io_counters(perdisk=True)[args.disk]
        data += (
            f"{(disk_io.read_count - prev_disk_io.read_count) / args.interval},"
            f"{(disk_io.write_count - prev_disk_io.write_count) / args.interval},"
            f"{(disk_io.read_bytes - prev_disk_io.read_bytes) / args.interval},"
            f"{(disk_io.write_bytes - prev_disk_io.write_bytes) / args.interval},"
        )

        net_io = psutil.net_io_counters(pernic=True)[args.net_iface]
        data += (
            f"{(net_io.packets_sent - prev_net_io.packets_sent) / args.interval},"
            f"{(net_io.packets_recv - prev_net_io.packets_recv) / args.interval},"
            f"{(net_io.bytes_sent - prev_net_io.bytes_sent) / args.interval},"
            f"{(net_io.bytes_recv - prev_net_io.bytes_recv) / args.interval}"
        )

        prev_disk_io = disk_io
        prev_net_io = net_io

        print(data)

        for cgroup_path in args.cgroup:
            cgroup_data = collect_cgroup_stat(cgroup_path)
            if cgroup_data is not None:
                print(f"{time_delta},{cgroup_path},{cgroup_data}")
