#!/bin/sh
# Create the symlinks used by the manual test docs in docs/test/.
# They are gitignored, so run this after cloning. Safe to run repeatedly.
set -eu

cd "$(dirname "$0")/../docs/test"

OUTSIDE=/tmp/ld-outside.md

if [ ! -e "$OUTSIDE" ]; then
    printf -- '---\ntitle: Outside Secret\n---\n\nThis file lives outside docs_dir and must never be served.\n' > "$OUTSIDE"
    echo "created $OUTSIDE"
else
    echo "exists  $OUTSIDE"
fi

# link NAME TARGET: create docs/test/NAME -> TARGET, replacing a symlink that points elsewhere
link() {
    if [ -L "$1" ]; then
        if [ "$(readlink "$1")" = "$2" ]; then
            echo "exists  docs/test/$1 -> $2"
            return
        fi
        rm "$1"
    elif [ -e "$1" ]; then
        echo "error: docs/test/$1 exists and is not a symlink" >&2
        exit 1
    fi
    ln -s "$2" "$1"
    echo "created docs/test/$1 -> $2"
}

link symlink-inside.md math.md
link symlinked-dir nested
link loop ..
link symlink-outside.md "$OUTSIDE"
