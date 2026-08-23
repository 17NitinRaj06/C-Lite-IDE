"""Built-in example programs shipped with the IDE."""

import os

from . import EXAMPLES_DIR


def list_examples():
    """Return a list of (category, title, path) tuples."""
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