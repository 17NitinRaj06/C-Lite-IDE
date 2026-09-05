"""C-Lite IDE - a lightweight C IDE for students with Turbo C compatibility."""

import os
import sys

APP_NAME = "C-Lite IDE"

if getattr(sys, "frozen", False):
    # Packaged exe: everything (compiler, include, runtime, examples,
    # icons) is copied next to the executable by packaging/build_ide.bat.
    ROOT = os.path.dirname(sys.executable)
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Writable user-data directory for settings, build output, and copied
# examples.  Lives in %LOCALAPPDATA% so non-admin users can write to it.
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", "")
if not LOCAL_APPDATA:
    LOCAL_APPDATA = os.path.join(os.path.expanduser("~"), "AppData", "Local")
USER_DATA_DIR = os.path.join(LOCAL_APPDATA, APP_NAME)

# Read version from central version.txt
_VERSION_FILE = os.path.join(ROOT, "version.txt")
try:
    with open(_VERSION_FILE, "r", encoding="utf-8") as _vf:
        APP_VERSION = _vf.read().strip()
except Exception:
    APP_VERSION = "1.0.0"

# Read-only bundled resources (install dir)
INCLUDE_DIR = os.path.join(ROOT, "include")
RUNTIME_DIR = os.path.join(ROOT, "runtime")
BUNDLED_EXAMPLES_DIR = os.path.join(ROOT, "examples")
BUNDLED_GCC_DIR = os.path.join(ROOT, "compiler")
COMPILER_DIR = os.path.join(BUNDLED_GCC_DIR, "mingw")
BUNDLED_GCC = os.path.join(COMPILER_DIR, "bin", "gcc.exe")

# Writable user-data paths
EXAMPLES_DIR = os.path.join(USER_DATA_DIR, "Examples")
BUILD_DIR = os.path.join(USER_DATA_DIR, "build")

RUNTIME_SOURCES = [
    "clite_startup.c",
    "conio_lite.c",
    "bgilite.c",
]

RUNTIME_LINK_LIBS = ["-lgdi32", "-lm"]
