"""Settings, themes and compiler discovery."""

import json
import os
import shutil

from . import ROOT, COMPILER_DIR, BUNDLED_GCC

SETTINGS_FILE = os.path.join(ROOT, "settings.json")

# Fallback locations only consulted when neither the bundled toolchain,
# the user-configured path, nor PATH has a usable gcc.
COMMON_GCC_PATHS = [
    r"C:\MinGW\bin\gcc.exe",
    r"C:\mingw64\bin\gcc.exe",
    r"C:\TDM-GCC-64\bin\gcc.exe",
    r"C:\msys64\mingw64\bin\gcc.exe",
    r"C:\msys64\mingw32\bin\gcc.exe",
]

THEMES = {
    "Light": {
        "window_bg": "#eceef0",
        "panel_bg": "#e4e6e9",
        "panel_fg": "#24292f",
        "editor_bg": "#ffffff",
        "editor_fg": "#24292f",
        "gutter_bg": "#eceef0",
        "gutter_fg": "#8a919e",
        "line_highlight": "#f4f7fb",
        "selection_bg": "#c7dbf5",
        "bracket_bg": "#dde7f3",
        "bracket_fg": "#24292f",
        "terminal_bg": "#f2f3f5",
        "terminal_fg": "#24292f",
        "accent": "#0078d7",
        "fg_muted": "#6b7280",
        "border": "#c8ccd4",
        "input_bg": "#ffffff",
        "input_fg": "#24292f",
        "btn_bg": "#f6f7f9",
        "btn_hover": "#e8ebef",
        "btn_press": "#dde1e6",
        "btn_fg": "#24292f",
        "fg_disabled": "#9aa1ac",
        "tab_bg": "#dde1e6",
        "tab_hover_bg": "#e4e8ec",
        "tab_active_bg": "#ffffff",
        "tab_fg": "#6b7280",
        "tab_active_fg": "#1f1f1f",
        "sel_bg": "#d6e6f8",
        "sel_fg": "#1f1f1f",
        "sb_bg": "#c8ccd4",
        "sb_hover": "#a6adb8",
        "sb_trough": "#eceef0",
        "sidebar_bg": "#e4e6e9",
        "bottom_bg": "#f2f3f5",
        "icon_folder": "#6b7280",
        "icon_file": "#8a919e",
        "menu_bg": "#ffffff",
        "menu_fg": "#24292f",
        "menu_hover": "#d6e6f8",
        "menu_hover_fg": "#000000",
        "menu_disabled": "#9aa1ac",
        "syntax": {
            "default": "#1f1f1f",
            "keyword": "#0000ff",
            "type": "#008080",
            "string": "#a31515",
            "char": "#a31515",
            "number": "#098658",
            "comment": "#008000",
            "preproc": "#800080",
            "function": "#795e26",
            "constant": "#0000ff",
        },
        "problems": {
            "error": "#c62828",
            "warning": "#b26a00",
            "info": "#1565c0",
            "hint": "#00695c",
        },
        "status_ok": "#1b7f3b",
        "status_err": "#c62828",
        "status_run": "#1565c0",
    },
    "Dark": {
        "window_bg": "#181a1f",
        "panel_bg": "#17191d",
        "panel_fg": "#c5cbd3",
        "editor_bg": "#1e2025",
        "editor_fg": "#c5cbd3",
        "gutter_bg": "#181a1f",
        "gutter_fg": "#5c6470",
        "line_highlight": "#21262e",
        "selection_bg": "#2e4a6e",
        "bracket_bg": "#333a44",
        "bracket_fg": "#e6e9ef",
        "terminal_bg": "#191b20",
        "terminal_fg": "#c5cbd3",
        "accent": "#4e8cc9",
        "fg_muted": "#8a919e",
        "border": "#2e333c",
        "input_bg": "#22252b",
        "input_fg": "#c5cbd3",
        "btn_bg": "#23272e",
        "btn_hover": "#2c313a",
        "btn_press": "#1d2026",
        "btn_fg": "#c5cbd3",
        "fg_disabled": "#5c6470",
        "tab_bg": "#1b1e24",
        "tab_hover_bg": "#20242b",
        "tab_active_bg": "#262b33",
        "tab_fg": "#8a919e",
        "tab_active_fg": "#e6e9ef",
        "sel_bg": "#2e4a6e",
        "sel_fg": "#e6e9ef",
        "sb_bg": "#333a44",
        "sb_hover": "#444d5c",
        "sb_trough": "#181a1f",
        "sidebar_bg": "#17191d",
        "bottom_bg": "#191b20",
        "icon_folder": "#7a8291",
        "icon_file": "#5c6470",
        "menu_bg": "#1b1e24",
        "menu_fg": "#c5cbd3",
        "menu_hover": "#2e4a6e",
        "menu_hover_fg": "#ffffff",
        "menu_disabled": "#6b7280",
        "syntax": {
            "default": "#c5cbd3",
            "keyword": "#a48bd1",
            "type": "#6fc2d9",
            "string": "#c89a74",
            "char": "#c89a74",
            "number": "#7bc3c0",
            "comment": "#67796c",
            "preproc": "#c08ac0",
            "function": "#5e9bd6",
            "constant": "#d6b264",
        },
        "problems": {
            "error": "#e06c75",
            "warning": "#d3a448",
            "info": "#5e9bd6",
            "hint": "#6cc5c0",
        },
        "status_ok": "#7cc98a",
        "status_err": "#e06c75",
        "status_run": "#5e9bd6",
    },
}

DEFAULT_SETTINGS = {
    "theme": "Light",
    "font_family": "Consolas",
    "font_size": 11,
    "tab_size": 4,
    "use_tabs": False,
    "compiler_path": "",
    "extra_flags": "",
    "auto_save_before_build": True,
    "run_timeout": 0,
    "recent_files": [],
    "last_dir": "",
}


def _merge(base, extra):
    out = dict(base)
    for k, v in (extra or {}).items():
        out[k] = v
    return out


class Settings:
    def __init__(self):
        self.data = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        try:
            if os.path.isfile(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
                    self.data = _merge(DEFAULT_SETTINGS, json.load(fh))
        except Exception:
            self.data = dict(DEFAULT_SETTINGS)

    def save(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def add_recent(self, path):
        rec = [p for p in self.get("recent_files", []) if p != path]
        rec.insert(0, path)
        self.set("recent_files", rec[:20])


def find_gcc(custom_path=""):
    """Locate a usable gcc executable.

    Priority:
      1. bundled toolchain (compiler\\mingw)
      2. user-configured path from Settings
      3. gcc on PATH
      4. other common install locations
    """
    if os.path.isfile(BUNDLED_GCC):
        return BUNDLED_GCC
    if custom_path and os.path.isfile(custom_path):
        return custom_path
    found = shutil.which("gcc")
    if found:
        return found
    for c in COMMON_GCC_PATHS:
        if os.path.isfile(c):
            return c
    return None


def compiler_source(custom_path=""):
    """Return (gcc_path, source_label) describing where the compiler is.

    source_label is one of "bundled", "custom", "path", "auto" or None
    when no compiler is found.
    """
    if os.path.isfile(BUNDLED_GCC):
        return BUNDLED_GCC, "bundled"
    if custom_path and os.path.isfile(custom_path):
        return custom_path, "custom"
    found = shutil.which("gcc")
    if found:
        return found, "path"
    for c in COMMON_GCC_PATHS:
        if os.path.isfile(c):
            return c, "auto"
    return None, None


def toolchain_root(gcc):
    """MinGW installation prefix for a gcc.exe path (two levels up from
    bin\\gcc.exe), or None."""
    if not gcc:
        return None
    root = os.path.dirname(os.path.dirname(gcc))
    return root if os.path.isdir(root) else None


def toolchain_bin(gcc):
    """The bin directory of a gcc toolchain (holds its runtime DLLs)."""
    root = toolchain_root(gcc)
    if not root:
        return None
    bindir = os.path.join(root, "bin")
    return bindir if os.path.isdir(bindir) else None


def gcc_version(gcc):
    """Return a short version string for the given gcc path, or None."""
    try:
        out = os.popen('"%s" --version' % gcc).read().splitlines()
        for line in out:
            if "gcc" in line.lower():
                return line.strip()
    except Exception:
        pass
    return None
