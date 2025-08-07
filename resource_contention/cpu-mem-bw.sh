if [ -z "$1" ]; then
  echo "Usage: $0 <num threads>"
  echo ""
  echo "Each thread spins for 100% CPU and uses as much memory bandwidth as possible."
  echo "More threads means more total memory bandwidth."
  exit 1
fi

# write causes double bandwidth as compared to read because data must be in cache before store can happen
# set memrate-wr-mbs and memrate-bytes large enough so they are not the limiting factor
exec stress-ng --memrate "$1" --memrate-wr-mbs 100000 --memrate-bytes 512m --memrate-method write64
