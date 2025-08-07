if [ -z "$1" ]; then
  echo "Usage: $0 <num threads> [cpu number]"
  echo ""
  echo "Each thread uses 100% CPU and constantly reads memory."
  echo "Size of memory used will be 70% of L2 Cache."
  echo "L2 Cache size is determined by cpu0, but that can be overriden."
  exit 1
fi

cpu=0
if [ -n "$2" ]; then
  cpu="$2"
fi

l2_info=$(cat /sys/devices/system/cpu/cpu"$cpu"/cache/index2/size)
l2_size=${l2_info%%[A-Z]*}
l2_unit=${l2_info##*[0-9]}
l2_scaled=$(bc <<< "$l2_size * 0.7")

echo "Exercising $l2_scaled$l2_unit of memory."

# note: use read64 instead of any write-based method because writes are eventually
# flushed through LLC and use up memory bandwidth
exec stress-ng --memrate $1 --memrate-bytes "$l2_scaled$l2_unit" --memrate-method read64
