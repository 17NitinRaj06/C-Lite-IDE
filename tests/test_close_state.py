import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clite_ide.app import App
from clite_ide import APP_NAME, APP_VERSION

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []


def check(name, ok):
    results.append((name, ok))
    print("%-46s %s" % (name, "PASS" if ok else "FAIL"))


def close_last_tab(app):
    nb = app.notebook
    tab = nb.tabs()[0]
    bx, by, bw, bh = nb._tab_regions()[tab]
    nb.event_generate("<Button-1>", x=bx + bw - 8, y=by + bh // 2)
    root.update()


def main():
    global root
    root = tk.Tk()
    app = App(root)
    root.update()

    # close the initial Untitled tab
    close_last_tab(app)
    root.update()

    # ---- last tab closed: clean state ----
    hello = os.path.join(ROOT, "examples", "console", "hello_world.c")
    app.open_file(hello)
    root.update()
    ed = app._current()
    check("title shows open filename",
          root.title() == "%s %s - [hello_world.c]" % (APP_NAME, APP_VERSION))
    check("statusbar shows full path",
          app.lbl_file.cget("text") == os.path.abspath(hello))

    app.close_tab(ed)
    root.update()
    check("no tabs left after close", len(app.notebook.tabs()) == 0)
    check("current cleared", app.current is None)
    check("title reset after close",
          root.title() == "%s %s" % (APP_NAME, APP_VERSION))
    check("statusbar path cleared", app.lbl_file.cget("text") == "")
    check("cursor position cleared", app.lbl_pos.cget("text") == "")

    # closed filename must not reappear after refresh/status/compile noise
    app._update_title()
    root.update()
    check("title stays clean after _update_title",
          root.title() == "%s %s" % (APP_NAME, APP_VERSION))
    app.status_msg("Build successful")
    app._update_title()
    root.update()
    check("no filename after status+refresh",
          app.lbl_file.cget("text") == "" and "hello_world" not in root.title())
    app._current()
    root.update()
    check("_current does not resurrect editor", app.current is None)

    # ---- closing one of several tabs switches to the new active tab ----
    dda = os.path.join(ROOT, "examples", "graphics", "dda_line.c")
    circle = os.path.join(ROOT, "examples", "graphics", "circle.c")
    app.open_file(dda)
    app.open_file(circle)
    root.update()
    active = app._current()
    active_path = os.path.abspath(active.filepath)
    check("title shows last opened tab",
          root.title().endswith("-%s]" % os.path.basename(active_path)) or
          root.title().endswith("- [%s]" % os.path.basename(active_path)))
    check("statusbar shows last opened path",
          app.lbl_file.cget("text") == active_path)

    # close the currently active tab -> notebook selects the remaining one
    app.close_tab(active)
    root.update()
    remaining = app._current()
    check("one tab remains", len(app.notebook.tabs()) == 1)
    check("current points at remaining tab", remaining is not None)
    check("title follows new active tab",
          root.title() == "%s %s - [%s]" % (APP_NAME, APP_VERSION,
                                            remaining.display_name()))
    check("statusbar follows new active tab",
          app.lbl_file.cget("text") == remaining.filepath)
    check("closed name not in title",
          os.path.basename(active_path) not in root.title())

    app.on_close()
    root.destroy()


main()
print("=== RESULTS ===")
ok = all(ok for _, ok in results)
for name, passed in results:
    print("%-46s %s" % (name, "PASS" if passed else "FAIL"))
sys.exit(0 if ok else 1)