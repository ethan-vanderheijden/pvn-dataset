if [ -z "$1" ]; then
  echo "Usage: $0 <num threads>"
  echo ""
  echo "Each thread spins for 100% CPU."
  echo "Only causes contention in CPU time, not in memory subsystem."
  exit 1
fi

exec stress-ng --nop "$1"
