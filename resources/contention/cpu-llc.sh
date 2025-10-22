if [ -z "$1" ]; then
  echo "Usage: $0 <num threads>"
  echo ""
  echo "Each thread uses 100% CPU and constantly reads memory."
  echo "Total memory used is 70% of L3 cache. Memory is evenly distributed among threads."
  echo "You should not create so many threads that each thread's memory is <= L2 cache size."
  exit 1
fi

l3_info=$(cat /sys/devices/system/cpu/cpu0/cache/index3/size)
l3_size=${l3_info%%[A-Z]*}
l3_unit=${l3_info##*[0-9]}
l3_each=$(bc <<< "($l3_size * 0.7) / $1")

echo "$1 threads, each using $l3_each$l3_unit of memory."

# note: use read64 instead of any write-based method because writes are eventually
# flushed through LLC and use up memory bandwidth
exec stress-ng --memrate $1 --memrate-bytes "$l3_each$l3_unit" --memrate-method read64
