"""Terminal panel: shows program output and accepts typed input."""

import tkinter as tk
from tkinter import ttk

from .settings import THEMES


class Terminal(ttk.Frame):
    def __init__(self, master, settings, on_input=None):
        super().__init__(master)
        self.settings = settings
        self.on_input = on_input
        self.process = None
        self._running = False

        self.text = tk.Text(self, wrap="char", state="disabled", bd=0,
                            padx=6, pady=4, insertwidth=0,
                            takefocus=False, cursor="arrow")
        self.text.tag_configure("header", foreground="#888888")
        self.text.tag_configure("ok", foreground="#1b7f3b")
        self.text.tag_configure("err", foreground="#c62828")
        self.text.tag_configure("echo", foreground="#888888")

        bar = ttk.Frame(self)
        self.lbl_state = ttk.Label(bar, text="Idle", width=16)
        self.btn_clear = ttk.Button(bar, text="Clear", width=8,
                                    command=self.clear)
        self.entry = ttk.Entry(bar)
        self.btn_send = ttk.Button(bar, text="Send", width=7,
                                   command=self.send_input)

        self.lbl_state.grid(row=0, column=0, padx=(6, 4))
        self.entry.grid(row=0, column=1, sticky="ew", padx=4)
        self.btn_send.grid(row=0, column=2, padx=(4, 2))
        self.btn_clear.grid(row=0, column=3, padx=(2, 6))
        bar.columnconfigure(1, weight=1)

        self.text.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=1, column=0, sticky="ew", pady=2)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.entry.bind("<Return>", lambda e: self.send_input())

        self.apply_theme(settings.get("theme", "Light"))

    def apply_theme(self, theme_name):
        t = THEMES.get(theme_name, THEMES["Light"])
        self.text.configure(bg=t["terminal_bg"], fg=t["terminal_fg"])
        self.text.tag_configure("header", foreground=t["gutter_fg"])
        self.text.tag_configure("ok", foreground=t["status_ok"])
        self.text.tag_configure("err", foreground=t["status_err"])
        self.text.tag_configure("echo", foreground=t["gutter_fg"])

    # ------------------------------------------------------------------

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def write(self, data):
        self.text.configure(state="normal")
        self.text.insert("end", data)
        self.text.see("end")
        self.text.configure(state="disabled")

    def write_line(self, data, tag=None):
        self.text.configure(state="normal")
        self.text.insert("end", data + "\n", tag)
        self.text.see("end")
        self.text.configure(state="disabled")

    def begin_run(self, label):
        self.clear()
        self.write_line("=== " + label + " ===", "header")
        self._running = True
        self.lbl_state.configure(text="Running")
        self.entry.configure(state="normal")
        self.entry.focus_set()

    def end_run(self, exit_code):
        self._running = False
        self.process = None
        self.lbl_state.configure(text="Finished")
        tag = "ok" if exit_code == 0 else "err"
        self.write_line("\nProcess finished with exit code %d" % exit_code,
                        tag)

    def note_error(self, message):
        self.write_line(message, "err")

    def set_process(self, proc):
        self.process = proc
        self.entry.configure(state="normal")

    def send_input(self):
        line = self.entry.get()
        if not line:
            return
        self.entry.delete(0, "end")
        self.write_line("> " + line, "echo")
        if self.on_input and self.process is not None:
            try:
                self.on_input(line)
            except (BrokenPipeError, OSError):
                self.write_line("(program no longer accepting input)", "err")

    def _enable_input(self, enabled):
        state = "normal" if enabled else "disabled"
        self.entry.configure(state=state)

    def set_running(self, running):
        self._running = running
        if running:
            self.lbl_state.configure(text="Running")
            self._enable_input(True)
        else:
            self.lbl_state.configure(text="Idle")
            self._enable_input(False)

    def is_running(self):
        return self._running
