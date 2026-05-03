#!/usr/bin/env bash
set -euo pipefail

BAUD=115200
PORT=""
LIST_ONLY=0

usage() {
  cat <<'EOF'
Usage: connect_badge_serial.sh [options]

Auto-detect a USB serial port for the badge and open picocom.

Options:
  -b, --baud RATE    Set baud rate (default: 115200)
  -p, --port DEVICE  Use specific serial device (example: /dev/ttyACM0)
  -l, --list         List detected candidate ports and exit
  -h, --help         Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -b|--baud)
      BAUD="${2:-}"
      shift 2
      ;;
    -p|--port)
      PORT="${2:-}"
      shift 2
      ;;
    -l|--list)
      LIST_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v picocom >/dev/null 2>&1; then
  echo "picocom is not installed. Install it with: sudo apt install -y picocom" >&2
  exit 1
fi

mapfile -t CANDIDATES < <(
  {
    ls -1 /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true
  } | sort -u
)

if [[ ${#CANDIDATES[@]} -eq 0 ]]; then
  echo "No USB serial devices found (/dev/ttyACM* or /dev/ttyUSB*)." >&2
  echo "Tip: reconnect badge, then run: dmesg | tail -n 50" >&2
  exit 1
fi

if [[ $LIST_ONLY -eq 1 ]]; then
  printf '%s\n' "${CANDIDATES[@]}"
  exit 0
fi

if [[ -z "$PORT" ]]; then
  if [[ ${#CANDIDATES[@]} -eq 1 ]]; then
    PORT="${CANDIDATES[0]}"
  else
    echo "Multiple serial ports found:"
    for i in "${!CANDIDATES[@]}"; do
      printf '  %d) %s\n' "$((i + 1))" "${CANDIDATES[i]}"
    done

    read -r -p "Select port number [1]: " PICK
    PICK="${PICK:-1}"

    if ! [[ "$PICK" =~ ^[0-9]+$ ]] || (( PICK < 1 || PICK > ${#CANDIDATES[@]} )); then
      echo "Invalid selection: $PICK" >&2
      exit 1
    fi

    PORT="${CANDIDATES[PICK - 1]}"
  fi
fi

if [[ ! -e "$PORT" ]]; then
  echo "Serial device does not exist: $PORT" >&2
  exit 1
fi

echo "Opening picocom on $PORT @ $BAUD..."
exec picocom -b "$BAUD" "$PORT"
