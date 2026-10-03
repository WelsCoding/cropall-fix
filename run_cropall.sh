#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

if [[ ! -d "$VENV_DIR" ]]; then
    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        echo "Python 3.12 was not found (or PYTHON_BIN is invalid)." >&2
        echo "Install Python 3.12 with its venv module, or set PYTHON_BIN to another Python 3 executable." >&2
        exit 1
    fi

    echo "Creating virtual environment at $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    python -m pip install --upgrade pip
    python -m pip install -r "$SCRIPT_DIR/requirements.txt"
else
    # If the venv already exists, deliberately do not reinstall or upgrade packages.
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Warning: ffmpeg is not installed; video preview and cropping will be unavailable." >&2
fi

if [[ $# -gt 0 && "$1" != /* ]]; then
    input_folder="$PWD/$1"
    shift
    set -- "$input_folder" "$@"
fi

cd "$SCRIPT_DIR"
exec python "$SCRIPT_DIR/cropall.py" "$@"
