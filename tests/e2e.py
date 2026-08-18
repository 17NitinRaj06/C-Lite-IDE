import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clite_ide.app import App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []


def step2(app):
    print("opening hello_world example")
    app.open_file(os.path.join(ROOT, "examples", "console", "hello_world.c"))
    print("compiling...")
    app.compile_current()
    root.after(2500, lambda: step3(app))


def step3(app):
    ok = not any(p["severity"] == "error" for p in app.problems._items)
    print("problems after compile:", app.problems._items)
    print("compile success:", ok)
    results.append(("compile", ok))
    print("running...")
    app.run_current()
    root.after(2500, lambda: step4(app))


def step4(app):
    out = app.terminal.text.get("1.0", "end")
    print("terminal contains 'Hello':", "Hello" in out)
    print("terminal content:\n", out)
    results.append(("run", "Hello" in out))
    root.after(500, lambda: step5(app))


def step5(app):
    print("opening graphics example")
    app.open_file(os.path.join(ROOT, "examples", "graphics", "circle.c"))
    app.compile_current()
    root.after(2500, lambda: step6(app))


def step6(app):
    ok = not any(p["severity"] == "error" for p in app.problems._items)
    print("graphics example compile success:", ok)
    results.append(("gfx_compile", ok))
    app.on_close()
    root.destroy()


root = tk.Tk()
app = App(root)
root.protocol("WM_DELETE_WINDOW", lambda: (app.on_close(), root.destroy()))
root.after(1500, lambda: step2(app))
root.mainloop()
print("=== RESULTS ===")
for name, ok in results:
    print("%-12s %s" % (name, "PASS" if ok else "FAIL"))
sys.exit(0 if all(ok for _, ok in results) else 1)