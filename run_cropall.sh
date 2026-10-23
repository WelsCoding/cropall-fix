#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIRED_PYTHON_VERSION="3.12"

PYTHON_BIN_WAS_SET=0
if [[ -n "${PYTHON_BIN:-}" ]]; then
    PYTHON_BIN_WAS_SET=1
fi
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

create_venv_with_uv() {
    echo "Creating virtual environment at $VENV_DIR with uv"
    if [[ "$PYTHON_BIN_WAS_SET" == 1 ]]; then
        if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
            echo "PYTHON_BIN is set to '$PYTHON_BIN', but no such executable was found." >&2
            exit 1
        fi
        # An explicitly requested interpreter always wins.
        uv venv --seed --python "$PYTHON_BIN" "$VENV_DIR"
    elif ! uv venv --seed --python "$REQUIRED_PYTHON_VERSION" \
        --python-preference only-system "$VENV_DIR"; then
        # Prefer the system/distro interpreter above: its Tk is linked
        # against the host X11/XCB libraries (and it is the interpreter
        # the python3-tk and ImageMagick packages target). uv-managed
        # ("standalone") CPython builds have shipped Tk builds that abort
        # on Linux with libxcb's "Unknown sequence number while appending
        # request" assertion (astral-sh/uv#15571). Only if there is no
        # system Python 3.12 do we let uv download a managed one, so that
        # the Python version is still guaranteed.
        echo "No system Python $REQUIRED_PYTHON_VERSION found; falling back to a uv-managed one." >&2
        uv venv --seed --python "$REQUIRED_PYTHON_VERSION" "$VENV_DIR"
    fi

    echo "Installing dependencies with uv pip"
    uv pip install --python "$VENV_DIR/bin/python" \
        -r "$SCRIPT_DIR/requirements.txt"
}

create_venv_with_python() {
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
}

if [[ ! -d "$VENV_DIR" ]]; then
    if command -v uv >/dev/null 2>&1; then
        create_venv_with_uv
    else
        create_venv_with_python
    fi
fi

# If the venv already exists it is used as-is: deliberately do not
# reinstall or upgrade packages. Delete .venv to rebuild it (e.g. with a
# different interpreter).
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

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
