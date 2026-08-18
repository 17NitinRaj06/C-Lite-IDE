"""Compile Log panel: raw compiler command and full GCC output."""

import tkinter as tk
from tkinter import ttk

from .settings import THEMES


def quote_arg(arg):
    """Quote an argument for display in the logged command line."""
    if " " in arg or "\t" in arg:
        return '"%s"' % arg.replace('"', '\\"')
    return arg


class CompileLog(ttk.Frame):
    """Read-only log of compiler invocations: the command that was run and
    the complete raw GCC output, kept separate from the program Terminal."""

    def __init__(self, master, settings):
        super().__init__(master)
        self.settings = settings

        self.text = tk.Text(self, wrap="char", state="disabled", bd=0,
                            padx=6, pady=4, insertwidth=0,
                            takefocus=False, cursor="arrow")

        bar = ttk.Frame(self)
        ttk.Label(bar, text="Compile Log").pack(side="left", padx=(6, 4))
        ttk.Button(bar, text="Clear", width=8,
                   command=self.clear).pack(side="right", padx=(2, 6))

        self.text.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=1, column=0, sticky="ew", pady=2)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.apply_theme(settings.get("theme", "Light"))

    def apply_theme(self, theme_name):
        t = THEMES.get(theme_name, THEMES["Light"])
        self.text.configure(bg=t["terminal_bg"], fg=t["terminal_fg"])
        self.text.tag_configure("header", foreground=t["gutter_fg"])
        self.text.tag_configure("dim", foreground=t["gutter_fg"])
        self.text.tag_configure("cmd", foreground=t["problems"]["info"])
        self.text.tag_configure("ok", foreground=t["status_ok"])
        self.text.tag_configure("err", foreground=t["status_err"])
        self.text.tag_configure("warn", foreground=t["problems"]["warning"])

    # ------------------------------------------------------------------

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def _write(self, data, tag=None):
        self.text.configure(state="normal")
        self.text.insert("end", data, tag)
        self.text.see("end")
        self.text.configure(state="disabled")

    def write(self, data):
        self._write(data)

    def write_line(self, data, tag=None):
        self._write(data + "\n", tag)

    def note_error(self, message):
        self.write_line(message, "err")

    # ------------------------------------------------------------------

    def begin(self, sources):
        """Start a new log entry for a compilation run."""
        self.clear()
        self.write_line("=== Compilation started ===", "header")
        for s in sources:
            self.write_line("  source: %s" % s, "dim")

    def log_command(self, cmd):
        self.write_line("Command:", "header")
        self.write_line("  " + " ".join(quote_arg(c) for c in cmd), "cmd")

    def log_output(self, output):
        if output and output.strip():
            self.write_line("--- compiler output ---", "header")
            self.write(output)
            if not output.endswith("\n"):
                self.write_line("")

    def end(self, success, exit_code, elapsed, errors=0, warnings=0):
        """Append the final success/failure summary."""
        if success:
            msg = "=== Compilation successful ==="
            if warnings:
                msg = "=== Compilation successful (%d warning%s) ===" % (
                    warnings, "s" if warnings != 1 else "")
            self.write_line("\n" + msg, "ok")
            self.write_line("Exit code: 0", "dim")
        else:
            msg = "=== Compilation FAILED ==="
            if errors:
                msg = "=== Compilation FAILED (%d error%s) ===" % (
                    errors, "s" if errors != 1 else "")
            self.write_line("\n" + msg, "err")
            self.write_line("Exit code: %d" % (exit_code or 1), "err")
        if elapsed is not None:
            self.write_line("Time: %.2fs" % elapsed, "dim")