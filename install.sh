#!/bin/sh
# Nilavu one-line installer: clone (into ./nilavu), set up .venv, install, first run.
# Quick start (bash/zsh/ksh, curl required):
#   sh <(curl -L https://raw.githubusercontent.com/jonathan-16bit/nilavu/main/install.sh)
# Fish users: DO NOT use the line above (<(...) is unsupported). Clone and run instead:
#   git clone https://github.com/jonathan-16bit/nilavu.git
#   cd nilavu
#   sh install.sh
set -eu

REPO_URL="https://github.com/jonathan-16bit/nilavu.git"
TARGET_DIR="./nilavu"

say() {
    printf '%s\n' "$1"
}

fail() {
    printf 'Error: %s\n' "$1" >&2
    exit 1
}

command -v git >/dev/null 2>&1 || fail "git is not installed. Install git, then re-run this script."
command -v python3 >/dev/null 2>&1 || fail "python3 is not installed. Install Python 3.11 or newer, then re-run this script."

# Enforce the same floor as pyproject.toml (requires-python >= 3.11).
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    python3 --version 2>/dev/null || true
    fail "Python 3.11+ is required. Update Python, then re-run this script."
fi

# Clone into the current directory (./nilavu), or reuse an existing checkout.
if [ -d "$TARGET_DIR/.git" ]; then
    say "Found existing checkout at $TARGET_DIR, updating it..."
    git -C "$TARGET_DIR" pull --ff-only
elif [ -e "$TARGET_DIR" ]; then
    fail "$TARGET_DIR already exists and is not a git checkout. Rename or remove it, then re-run this script."
else
    say "Cloning Nilavu into $TARGET_DIR ..."
    git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"

# Same steps as the README manual install, just automated.
if [ ! -x ".venv/bin/python" ]; then
    say "Creating virtual environment (.venv) ..."
    if ! python3 -m venv .venv; then
        printf '%s\n' "Could not create .venv with 'python3 -m venv .venv'." >&2
        printf '%s\n' "On Debian/Ubuntu you may need: sudo apt install python3-venv" >&2
        exit 1
    fi
else
    say "Reusing existing virtual environment (.venv) ..."
fi

say "Installing Nilavu dependencies ..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .

say "Starting Nilavu for the first time ..."
exec .venv/bin/python -m nilavu --game --seed fern
