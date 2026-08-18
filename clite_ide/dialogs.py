"""Small themed modal dialogs: text input, integer input, yes/no
confirmations and notices.  Replaces the native tk simpledialog /
messagebox windows so every dialog matches the active theme."""

import tkinter as tk
from tkinter import ttk

from .settings import THEMES

_theme = "Light"


def apply_theme(name):
    global _theme
    _theme = name


def _t():
    return THEMES.get(_theme, THEMES["Light"])


def _center(parent, dlg):
    dlg.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dlg.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dlg.winfo_height()) // 2
    dlg.geometry("+%d+%d" % (x, y))


def _modal(parent, title, message, buttons):
    t = _t()
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=t["window_bg"])
    dlg.transient(parent)
    dlg.resizable(False, False)
    result = []

    def choose(value):
        result.append(value)
        dlg.destroy()

    dlg.protocol("WM_DELETE_WINDOW", lambda: choose(None))
    if message:
        ttk.Label(dlg, text=message, padding=(16, 14, 16, 0)).pack(anchor="w")
    bfrm = ttk.Frame(dlg)
    bfrm.pack(fill="x", padx=16, pady=(12, 12))
    for label, value in buttons:
        ttk.Button(bfrm, text=label, width=12,
                   command=lambda v=value: choose(v)).pack(
            side="left", padx=(0, 6))
    _center(parent, dlg)
    dlg.lift()
    dlg.grab_set()
    parent.wait_window(dlg)
    return result[0] if result else None


def ask_string(parent, title, prompt, initial=""):
    t = _t()
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=t["window_bg"])
    dlg.transient(parent)
    dlg.resizable(False, False)
    result = []
    var = tk.StringVar(value=initial)

    def choose(value):
        result.append(value)
        dlg.destroy()

    dlg.protocol("WM_DELETE_WINDOW", lambda: choose(None))
    ttk.Label(dlg, text=prompt, padding=(16, 14, 16, 0)).pack(anchor="w")
    frm = ttk.Frame(dlg)
    frm.pack(fill="x", padx=16, pady=10)
    ent = ttk.Entry(frm, textvariable=var, width=30)
    ent.grid(row=0, column=0)
    frm.columnconfigure(0, weight=1)
    ent.focus_set()
    ent.selection_range(0, "end")
    ent.bind("<Return>", lambda e: choose(var.get()))
    ent.bind("<Escape>", lambda e: choose(None))
    bfrm = ttk.Frame(dlg)
    bfrm.pack(fill="x", padx=16, pady=(4, 12))
    ttk.Button(bfrm, text="OK", width=10,
               command=lambda: choose(var.get())).pack(side="left",
                                                       padx=(0, 6))
    ttk.Button(bfrm, text="Cancel", width=10,
               command=lambda: choose(None)).pack(side="left")
    _center(parent, dlg)
    dlg.lift()
    dlg.grab_set()
    parent.wait_window(dlg)
    return result[0] if result else None


def ask_int(parent, title, prompt, minvalue=None, maxvalue=None,
            initialvalue=None):
    t = _t()
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=t["window_bg"])
    dlg.transient(parent)
    dlg.resizable(False, False)
    result = []
    start = initialvalue if initialvalue is not None else \
        (minvalue if minvalue is not None else 1)
    var = tk.StringVar(value=str(start))

    def choose(value):
        result.append(value)
        dlg.destroy()

    def ok():
        try:
            v = int(var.get())
        except ValueError:
            return
        if minvalue is not None and v < minvalue:
            return
        if maxvalue is not None and v > maxvalue:
            return
        choose(v)

    dlg.protocol("WM_DELETE_WINDOW", lambda: choose(None))
    ttk.Label(dlg, text=prompt, padding=(16, 14, 16, 0)).pack(anchor="w")
    frm = ttk.Frame(dlg)
    frm.pack(fill="x", padx=16, pady=10)
    ent = ttk.Entry(frm, textvariable=var, width=16)
    ent.grid(row=0, column=0)
    ent.focus_set()
    ent.selection_range(0, "end")
    ent.bind("<Return>", lambda e: ok())
    ent.bind("<Escape>", lambda e: choose(None))
    bfrm = ttk.Frame(dlg)
    bfrm.pack(fill="x", padx=16, pady=(4, 12))
    ttk.Button(bfrm, text="OK", width=10, command=ok).pack(side="left",
                                                           padx=(0, 6))
    ttk.Button(bfrm, text="Cancel", width=10,
               command=lambda: choose(None)).pack(side="left")
    _center(parent, dlg)
    dlg.lift()
    dlg.grab_set()
    parent.wait_window(dlg)
    return result[0] if result else None


def ask_yes_no(parent, title, message):
    return _modal(parent, title, message,
                  (("Yes", True), ("No", False)))


def ask_yes_no_cancel(parent, title, message):
    return _modal(parent, title, message,
                  (("Yes", True), ("No", False), ("Cancel", None)))


def _notice(parent, title, message, icon):
    t = _t()
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=t["window_bg"])
    dlg.transient(parent)
    dlg.resizable(False, False)
    ttk.Label(dlg, text=message, padding=(16, 14, 16, 0)).pack(anchor="w")
    bfrm = ttk.Frame(dlg)
    bfrm.pack(fill="x", padx=16, pady=(12, 12))
    ttk.Button(bfrm, text="OK", width=12,
               command=dlg.destroy).pack(side="left")
    _center(parent, dlg)
    dlg.lift()
    dlg.grab_set()
    parent.wait_window(dlg)


def show_warning(parent, title, message):
    _notice(parent, title, message, "warning")


def show_error(parent, title, message):
    _notice(parent, title, message, "error")


def show_info(parent, title, message):
    _notice(parent, title, message, "info")