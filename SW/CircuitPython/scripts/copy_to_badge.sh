#!/usr/bin/env bash
set -euo pipefail

MOUNTPOINT=""
TARGET_SUBDIR=""
DRY_RUN=0
SOURCES=()

auto_detect_mountpoint() {
  local mp=""

  # Common Linux mount locations for CIRCUITPY.
  for path in \
    "/media/$USER/CIRCUITPY" \
    "/run/media/$USER/CIRCUITPY" \
    "/mnt/CIRCUITPY" \
    "/Volumes/CIRCUITPY"; do
    if [[ -d "$path" ]]; then
      mp="$path"
      break
    fi
  done

  if [[ -z "$mp" ]] && command -v lsblk >/dev/null 2>&1; then
    mp="$(lsblk -o LABEL,MOUNTPOINT -nr | awk '$1=="CIRCUITPY" && $2!="" {print $2; exit}')"
  fi

  printf '%s' "$mp"
}

usage() {
  cat <<'EOF'
Usage: copy_to_badge.sh [options] [FILES_OR_DIRS...]

Copy CircuitPython files/folders to a mounted CIRCUITPY drive.

If no source is provided, it copies ./code.py.

Options:
  -m, --mount PATH   CIRCUITPY mountpoint (auto-detected if omitted)
  -s, --source PATH  Source file/directory to copy (can be used multiple times)
  -t, --target DIR   Target subdirectory inside CIRCUITPY (default: root)
  -n, --dry-run      Print operations without copying
  -h, --help         Show this help

Examples:
  copy_to_badge.sh code.py
  copy_to_badge.sh code.py Bitmap.h
  copy_to_badge.sh --source ../examples/mb_code.py
  copy_to_badge.sh -s code.py -s lib/
  copy_to_badge.sh --target lib my_module/
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--mount)
      MOUNTPOINT="${2:-}"
      shift 2
      ;;
    -s|--source)
      if [[ -z "${2:-}" ]]; then
        echo "Missing argument for $1" >&2
        usage >&2
        exit 1
      fi
      SOURCES+=("$2")
      shift 2
      ;;
    -t|--target)
      TARGET_SUBDIR="${2:-}"
      shift 2
      ;;
    -n|--dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [[ -z "$MOUNTPOINT" ]]; then
  MOUNTPOINT="$(auto_detect_mountpoint)"
fi

if [[ -z "$MOUNTPOINT" || ! -d "$MOUNTPOINT" ]]; then
  echo "Could not find mounted CIRCUITPY drive." >&2
  echo "Pass it explicitly, for example: --mount /media/$USER/CIRCUITPY" >&2
  exit 1
fi

DEST="$MOUNTPOINT"
if [[ -n "$TARGET_SUBDIR" ]]; then
  DEST="$MOUNTPOINT/${TARGET_SUBDIR#/}"
fi

if [[ $DRY_RUN -eq 0 ]]; then
  mkdir -p "$DEST"
fi

if [[ $# -gt 0 ]]; then
  SOURCES+=("$@")
fi

if [[ ${#SOURCES[@]} -eq 0 ]]; then
  SOURCES=("code.py")
fi

for src in "${SOURCES[@]}"; do
  if [[ ! -e "$src" ]]; then
    echo "Source not found: $src" >&2
    exit 1
  fi

done

echo "CIRCUITPY: $MOUNTPOINT"
echo "Target:    $DEST"

for src in "${SOURCES[@]}"; do
  if [[ -d "$src" ]]; then
    if [[ $DRY_RUN -eq 1 ]]; then
      echo "[dry-run] cp -R '$src' '$DEST/'"
    else
      cp -R "$src" "$DEST/"
      echo "Copied directory: $src"
    fi
  else
    if [[ $DRY_RUN -eq 1 ]]; then
      echo "[dry-run] cp '$src' '$DEST/'"
    else
      cp "$src" "$DEST/"
      echo "Copied file: $src"
    fi
  fi
done

if [[ $DRY_RUN -eq 0 ]]; then
  sync
  echo "Done. Files copied to $DEST"
fi
