import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clite_ide.app import App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []


def send(app, text):
    app.terminal.entry.delete(0, "end")
    app.terminal.entry.insert(0, text)
    app.terminal.send_input()


def wait_build_done(app, step):
    if app.build_busy:
        root.after(500, lambda: wait_build_done(app, step))
        return
    step(app)


def wait_launched(app, step):
    if app.runner.process is None:
        root.after(500, lambda: wait_launched(app, step))
        return
    step(app)


def step2(app):
    app.open_file(os.path.join(ROOT, "examples", "graphics", "dda_line.c"))
    print("compiling dda_line...")
    app.compile_current()
    root.after(500, lambda: wait_build_done(app, step3))


def step3(app):
    ok = not any(p["severity"] == "error" for p in app.problems._items)
    print("dda compile ok:", ok)
    results.append(("compile", ok))
    app.run_current()
    root.after(500, lambda: wait_launched(app, step4))


def step4(app):
    print("sending input: 10 10")
    send(app, "10 10")
    root.after(300, lambda: step5(app))


def step5(app):
    print("sending input: 300 300")
    send(app, "300 300")
    root.after(2500, lambda: step6(app))


def step6(app):
    out = app.terminal.text.get("1.0", "end")
    print("prompts shown:", "Enter starting point" in out)
    print("terminal:\n", out)
    results.append(("prompts", "Enter starting point" in out))
    print("sending key for getch()")
    send(app, "q")
    root.after(1500, lambda: step7(app))


def step7(app, tries=0):
    out = app.terminal.text.get("1.0", "end")
    if "exit code 0" not in out and tries < 20:
        root.after(500, lambda: step7(app, tries + 1))
        return
    print("process exited cleanly:", "exit code 0" in out)
    results.append(("exit0", "exit code 0" in out))
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