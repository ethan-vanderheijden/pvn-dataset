#!/usr/bin/env python3

import argparse
import psutil
import time

parser = argparse.ArgumentParser(
    description="Measures and reports system-wide resource utilization."
)
parser.add_argument("disk", type=str, help="Disk device to monitor (e.g., sda1)")
parser.add_argument("net_iface", type=str, help="Network interface to monitor (e.g., eth0)")
parser.add_argument(
    "-i", "--interval", type=int, default=5, help="Interval in seconds between measurements"
)
args = parser.parse_args()

print(
    "time,"
    "cpu,"
    "mem_total,mem_available,mem_used,mem_buf_cache,"
    "disk_r_rate,disk_w_rate,disk_r_bytes_rate,disk_w_bytes_rate,"
    "net_sent_pps,net_recv_pps,net_sent_bps,net_recv_bps"
)

if __name__ == "__main__":
    start = time.time()
    psutil.cpu_percent(interval=None, percpu=True)
    prev_disk_io = psutil.disk_io_counters(perdisk=True)[args.disk]
    prev_net_io = psutil.net_io_counters(pernic=True)[args.net_iface]

    count = 1
    while True:
        now = time.time()
        time.sleep(count * args.interval - (now - start))
        count += 1

        cpu = sum(psutil.cpu_percent(interval=None, percpu=True))
        data = f"{int(now - start)},{cpu},"

        mem = psutil.virtual_memory()
        data += f"{mem.total},{mem.available},{mem.used},{mem.buffers + mem.cached},"

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
