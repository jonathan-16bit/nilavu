#!/bin/sh
# Nilavu one-line installer: reuse the current checkout (or clone into ./nilavu),
# set up .venv, install, first run.
# Quick start (bash/zsh/ksh, curl required):
#   sh <(curl -fL https://raw.githubusercontent.com/jonathan-16bit/nilavu/main/install.sh)
# (-f makes curl fail explicitly on HTTP errors instead of saving an error page.)
# Fish users: DO NOT use the line above (<(...) is unsupported). Clone and run instead:
#   git clone https://github.com/jonathan-16bit/nilavu.git
#   cd nilavu
#   sh install.sh
set -eu

REPO_URL="https://github.com/jonathan-16bit/nilavu.git"
TARGET_DIR="./nilavu"
PROJECT_DIR=""

say() {
    printf '%s\n' "$1"
}

fail() {
    printf 'Error: %s\n' "$1" >&2
    exit 1
}

check_origin() {
    dir=$1
    origin_url=$(git -C "$dir" remote get-url origin 2>/dev/null) \
        || fail "No 'origin' remote in $dir. Clone $REPO_URL first, then re-run."
    case "$origin_url" in
        *nilavu.git|*nilavu)
            say "Remote origin: $origin_url"
            ;;
        *)
            fail "Unexpected origin '$origin_url' in $dir; expected a nilavu checkout."
            ;;
    esac
}

ensure_clean() {
    dir=$1
    if [ -n "$(git -C "$dir" status --porcelain)" ]; then
        fail "$dir has uncommitted changes. Commit, stash, or discard them, then re-run."
    fi
}

command -v git >/dev/null 2>&1 || fail "git is not installed. Install git, then re-run this script."
command -v python3 >/dev/null 2>&1 || fail "python3 is not installed. Install Python 3.11 or newer, then re-run this script."

# Enforce the same floor as pyproject.toml (requires-python >= 3.11).
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    python3 --version 2>/dev/null || true
    fail "Python 3.11+ is required. Update Python, then re-run this script."
fi

# Reuse the current checkout when run from inside one, so the manual fallback
# (clone, cd nilavu, sh install.sh) does not nest a nilavu/nilavu checkout.
if [ -d "./.git" ] && [ -f "./pyproject.toml" ] && [ -d "./src/nilavu" ]; then
    say "Reusing current checkout (.) ..."
    PROJECT_DIR="."
elif [ -d "$TARGET_DIR/.git" ]; then
    say "Found existing checkout at $TARGET_DIR, updating it..."
    PROJECT_DIR="$TARGET_DIR"
elif [ -e "$TARGET_DIR" ]; then
    fail "$TARGET_DIR already exists and is not a git checkout. Rename or remove it, then re-run this script."
else
    say "Cloning Nilavu into $TARGET_DIR ..."
    git clone "$REPO_URL" "$TARGET_DIR"
    PROJECT_DIR="$TARGET_DIR"
fi

check_origin "$PROJECT_DIR"
ensure_clean "$PROJECT_DIR"
if ! git -C "$PROJECT_DIR" pull --ff-only; then
    fail "Could not fast-forward $PROJECT_DIR. Resolve any diverged history, then re-run."
fi

cd "$PROJECT_DIR"

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
