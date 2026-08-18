import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clite_ide.app import App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []


def check(name, ok):
    results.append((name, ok))
    print("%-44s %s" % (name, "PASS" if ok else "FAIL"))


def click_button(root, text):
    def walk(w):
        for sub in w.winfo_children():
            if isinstance(sub, tk.ttk.Button) and sub.cget("text") == text:
                sub.invoke()
                return True
            if walk(sub):
                return True
        return False

    for child in root.winfo_children():
        if walk(child):
            return


def main():
    root = tk.Tk()
    app = App(root)
    root.update()

    # Move the IDE away from the screen origin to prove relative centering.
    root.geometry("1024x680+300+200")
    root.update()

    ed = app._current()
    ed.content.insert("end", "\n// unsaved")
    root.update()

    state = {"ok": False, "done": False}

    def inspect_dialog():
        dlg = None
        for child in root.winfo_children():
            if isinstance(child, tk.Toplevel) and child.winfo_exists():
                dlg = child
        if not dlg:
            return
        rx, ry = root.winfo_rootx(), root.winfo_rooty()
        rw, rh = root.winfo_width(), root.winfo_height()
        dw, dh = dlg.winfo_width(), dlg.winfo_height()
        cx, cy = rx + (rw - dw) // 2, ry + (rh - dh) // 2
        gx, gy = [int(v) for v in dlg.geometry().split("+")[1:]]
        state["ok"] = (gx == cx and gy == cy)
        state["done"] = True
        click_button(root, "Cancel")

    root.after(600, inspect_dialog)
    app.close_tab(app._current())  # blocks until the dialog is dismissed
    root.update()
    check("Unsaved dialog centered on IDE window", state["done"] and state["ok"])
    check("dialog closes via Cancel, tab kept", len(app.notebook.tabs()) == 1)

    # Teardown without re-opening the dialog: clear dirty state, then close.
    app._current().set_text("")
    app.close_tab(app._current())
    root.update()
    check("clean close after dialog", len(app.notebook.tabs()) == 0)

    app.on_close()
    root.destroy()


main()
print("=== RESULTS ===")
ok = all(ok for _, ok in results)
for name, passed in results:
    print("%-44s %s" % (name, "PASS" if passed else "FAIL"))
sys.exit(0 if ok else 1)