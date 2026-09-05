"""Built-in example programs shipped with the IDE."""

import os
import shutil

from . import BUNDLED_EXAMPLES_DIR, EXAMPLES_DIR


def ensure_examples_copied():
    """Copy bundled examples to the writable user-data directory on
    first run (or if the destination is missing)."""
    if not os.path.isdir(BUNDLED_EXAMPLES_DIR):
        return
    for category in ("console", "graphics"):
        src_dir = os.path.join(BUNDLED_EXAMPLES_DIR, category)
        if not os.path.isdir(src_dir):
            continue
        dst_dir = os.path.join(EXAMPLES_DIR, category)
        if not os.path.isdir(dst_dir):
            os.makedirs(dst_dir, exist_ok=True)
            for fname in os.listdir(src_dir):
                src = os.path.join(src_dir, fname)
                dst = os.path.join(dst_dir, fname)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)


def list_examples():
    """Return a list of (category, title, path) tuples."""
    ensure_examples_copied()
    result = []
    for category in ("console", "graphics"):
        directory = os.path.join(EXAMPLES_DIR, category)
        if not os.path.isdir(directory):
            continue
        for fname in sorted(os.listdir(directory)):
            if fname.lower().endswith((".c", ".cpp", ".cc", ".cxx")):
                title = (os.path.splitext(fname)[0]
                         .replace("_", " ").title())
                result.append((category, title,
                               os.path.join(directory, fname)))
    return result