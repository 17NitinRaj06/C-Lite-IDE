import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clite_ide.app import App
from clite_ide.tabs import CLOSE_GLYPH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []


def check(name, ok):
    results.append((name, ok))
    print("%-34s %s" % (name, "PASS" if ok else "FAIL"))


def main():
    root = tk.Tk()
    app = App(root)
    root.update()

    # App starts with one "Untitled.c" tab; close it via the X button.
    nb = app.notebook
    untitled = nb.tabs()[0]
    bx, by, bw, bh = nb._tab_regions()[untitled]
    nb.event_generate("<Button-1>", x=bx + bw - 8, y=by + bh // 2)
    root.update()
    check("initial tab closed via X", len(nb.tabs()) == 0)

    files = ["hello_world.c", "dda_line.c", "circle.c"]
    paths = [os.path.join(ROOT, "examples", "graphics", f)
             if f != "hello_world.c"
             else os.path.join(ROOT, "examples", "console", f)
             for f in files]
    for p in paths:
        app.open_file(p)
    root.update()

    check("opened 3 tabs", len(nb.tabs()) == 3)
    tabs = nb.tabs()

    active = tabs[nb.index("current")]
    check("active tab shows X", CLOSE_GLYPH in nb.tab(active, "text"))

    inactive = [t for t in tabs if t != active][0]
    check("inactive tab hides X", CLOSE_GLYPH not in nb.tab(inactive, "text"))

    ix, iy, iw, ih = nb._tab_regions()[inactive]
    nb.event_generate("<Motion>", x=ix + 6, y=iy + ih // 2)
    root.update()
    check("inactive tab shows X on hover", CLOSE_GLYPH in nb.tab(inactive, "text"))

    nb.event_generate("<Leave>", x=ix + 6, y=iy + ih // 2)
    root.update()
    check("inactive tab hides X after leave", CLOSE_GLYPH not in nb.tab(inactive, "text"))

    before = len(nb.tabs())
    nb.event_generate("<Motion>", x=ix + 6, y=iy + ih // 2)
    root.update()
    check("hover before X click shows X", CLOSE_GLYPH in nb.tab(inactive, "text"))
    hx, hy, hw, hh = nb._tab_regions()[inactive]
    nb.event_generate("<Button-1>", x=hx + hw - 8, y=hy + hh // 2)
    root.update()
    check("X click closes only that tab", len(nb.tabs()) == before - 1)
    check("closed the right tab", inactive not in nb.tabs())
    check("remaining tabs intact",
          all(getattr(nb.nametowidget(t), "editor", None) for t in nb.tabs()))

    active = nb.tabs()[nb.index("current")]
    ax, ay, aw, ah = nb._tab_regions()[active]
    nb.event_generate("<Button-1>", x=ax + aw - 8, y=ay + ah // 2)
    root.update()
    check("X click closes active tab", len(nb.tabs()) == 1)

    # click NOT on the X must select, not close
    last = nb.tabs()[0]
    lx, ly, lw, lh = nb._tab_regions()[last]
    nb.event_generate("<Button-1>", x=lx + 6, y=ly + lh // 2)
    root.update()
    check("click on label does not close", len(nb.tabs()) == 1)
    check("click on label selects tab", nb.index("current") == 0)

    # dirty file: Don't Save closes
    ed = app._current()
    ed.content.insert("end", "\n// unsaved change")
    root.update()
    check("dirty state detected", app.current.is_dirty())

    def click_button(text):
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

    root.after(800, lambda: click_button("Don't Save"))
    app.close_tab(app._current())
    root.update()
    check("dirty close with Don't Save closes", len(nb.tabs()) == 0)

    # dirty file: Cancel keeps the tab open
    app.open_file(os.path.join(ROOT, "examples", "graphics", "circle.c"))
    root.update()
    ed = app._current()
    ed.content.insert("end", "\n// keep me")
    root.update()
    root.after(800, lambda: click_button("Cancel"))
    app.close_tab(app._current())
    root.update()
    check("dirty close with Cancel keeps tab", len(nb.tabs()) == 1)

    # dirty file: Save writes the file and closes the tab
    saved = open(ed.filepath, encoding="utf-8").read()
    try:
        root.after(800, lambda: click_button("Save"))
        app.close_tab(app._current())
        root.update()
        check("dirty close with Save closes", len(nb.tabs()) == 0)
        check("dirty close with Save wrote file",
              "\n// keep me" in open(ed.filepath, encoding="utf-8").read())
    finally:
        with open(ed.filepath, "w", encoding="utf-8") as fh:
            fh.write(saved)

    app.on_close()
    root.destroy()


main()
print("=== RESULTS ===")
ok = all(ok for _, ok in results)
for name, passed in results:
    print("%-34s %s" % (name, "PASS" if passed else "FAIL"))
sys.exit(0 if ok else 1)