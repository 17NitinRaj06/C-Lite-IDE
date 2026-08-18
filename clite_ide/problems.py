"""Problems panel: clickable list of compiler errors and warnings."""

import os
import tkinter as tk
from tkinter import ttk

from .settings import THEMES


class Problems(ttk.Frame):
    def __init__(self, master, settings, on_navigate=None):
        super().__init__(master)
        self.settings = settings
        self.on_navigate = on_navigate
        self._items = []

        cols = ("sev", "message", "file", "line")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                 selectmode="browse")
        self.tree.heading("sev", text="")
        self.tree.heading("message", text="Message")
        self.tree.heading("file", text="File")
        self.tree.heading("line", text="Line")
        self.tree.column("sev", width=70, anchor="center", stretch=False)
        self.tree.column("message", width=460, anchor="w")
        self.tree.column("file", width=180, anchor="w")
        self.tree.column("line", width=50, anchor="e", stretch=False)

        vs = ttk.Scrollbar(self, orient="vertical",
                           command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_activate)
        self.tree.bind("<Return>", self._on_activate)
        self.tree.tag_configure("error", foreground="#c62828")
        self.tree.tag_configure("warning", foreground="#b26a00")
        self.tree.tag_configure("info", foreground="#1565c0")
        self.tree.tag_configure("hint", foreground="#00695c")

        self.lbl_count = ttk.Label(self, text="No problems", padding=2)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.lbl_count.grid(row=1, column=0, columnspan=2, sticky="w")

    def apply_theme(self, theme_name):
        t = THEMES.get(theme_name, THEMES["Light"])
        self.tree.tag_configure("error", foreground=t["problems"]["error"])
        self.tree.tag_configure("warning",
                                foreground=t["problems"]["warning"])
        self.tree.tag_configure("info", foreground=t["problems"]["info"])
        self.tree.tag_configure("hint", foreground=t["problems"]["hint"])

    # ------------------------------------------------------------------

    def set_problems(self, items):
        """items: list of dicts {severity, message, file, line, col}"""
        self._items = items
        self.tree.delete(*self.tree.get_children())
        for it in items:
            sev = it.get("severity", "error")
            label = {"error": "Error", "warning": "Warning",
                     "info": "Info", "hint": "Hint"}.get(sev, sev)
            fname = os.path.basename(it.get("file", ""))
            self.tree.insert("", "end", values=(label, it.get("message"),
                                                fname,
                                                it.get("line", "")),
                             tags=(sev,))
        if not items:
            self.lbl_count.configure(text="No problems")
        else:
            nerr = sum(1 for i in items if i.get("severity") == "error")
            nwar = sum(1 for i in items if i.get("severity") == "warning")
            self.lbl_count.configure(
                text="%d problems (%d errors, %d warnings)"
                     % (len(items), nerr, nwar))

    def _on_activate(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        idx = self.tree.index(iid)
        if 0 <= idx < len(self._items):
            it = self._items[idx]
            if self.on_navigate and it.get("file"):
                self.on_navigate(it.get("file"), it.get("line", 1))

    def clear(self):
        self.set_problems([])