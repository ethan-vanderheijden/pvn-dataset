if [ -z "$1" ]; then
  echo "Usage: $0 <num threads> [interval seconds]"
  echo ""
  echo "Each thread uses X% CPU where X ramp up from 0->100 in increments of 20%."
  echo "X lasts at a particular level for interval seconds (default 60s)."
  echo "The final increment is 200% CPU, where double the threads are used."
  exit 1
fi

interval=60
if [ -n "$2" ]; then
  interval="$2"
fi

for cpu in 0 20 40 60 80 100; do
  echo "Starting $1 threads at $cpu% CPU for $interval seconds"
  stress-ng --cpu "$1" --cpu-method sieve --cpu-load "$cpu" --timeout "$interval"s
done

threads=$(( $1 * 2 ))
echo "Starting $threads threads at 100% CPU for $interval seconds"
stress-ng --cpu "$threads" --cpu-method sieve --cpu-load 100 --timeout "$interval"s
