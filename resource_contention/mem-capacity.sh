if [ -z "$1" ]; then
  echo "Usage: $0 <% of total memory to allocate>"
  echo ""
  echo "Allocates the specified percentage of total system memory and continually writes to it."
  echo "This uses up 100% of the CPU."
  exit 1
fi

mem=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
target_mem=$(bc <<< "${mem} * $1 / 100")
stress-ng -m 1 --vm-keep --vm-bytes "${target_mem}k"
