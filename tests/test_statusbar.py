import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clite_ide.app import App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []


def check(name, ok):
    results.append((name, ok))
    print("%-52s %s" % (name, "PASS" if ok else "FAIL"))


def main():
    global root
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.on_close(), root.destroy()))

    # ------------------------------------------------------------------
    def step1():
        ed = app._current()
        check("initial tab present", ed is not None)

        ed.content.insert("1.0", "alpha\nbeta")
        ed.content.mark_set("insert", "2.0")
        app._on_cursor(ed, 2, 0)
        root.update()
        check("Lines updates on edit",
              app.lbl_lines.cget("text") == "Lines: 2")
        check("Ln/Col follows cursor",
              app.lbl_pos.cget("text") == "Ln 2, Col 0")
        check("no selection shows Sel: 0",
              app.lbl_sel.cget("text") == "Sel: 0")

        ed.content.mark_set("insert", "1.3")
        app._on_cursor(ed, 1, 3)
        root.update()
        check("cursor move updates Ln/Col",
              app.lbl_pos.cget("text") == "Ln 1, Col 3")

        ed.content.tag_add("sel", "1.0", "1.3")
        app._on_cursor(ed, 1, 3)
        root.update()
        check("selected chars shown", app.lbl_sel.cget("text") == "Sel: 3")
        ed.content.tag_remove("sel", "1.0", "end")
        app._on_cursor(ed, 1, 3)
        root.update()
        check("Sel resets to 0", app.lbl_sel.cget("text") == "Sel: 0")

        step2()

    # ------------------------------------------------------------------
    def step2():
        dda = os.path.join(ROOT, "examples", "graphics", "dda_line.c")
        circle = os.path.join(ROOT, "examples", "graphics", "circle.c")
        app.open_file(dda)
        app.open_file(circle)
        root.update()
        ed_dda = None
        holder_dda = None
        for h in app.notebook.tabs():
            frame = app.notebook.nametowidget(h)
            edx = getattr(frame, "editor", None)
            if edx and edx.filepath and \
                    os.path.basename(edx.filepath) == "dda_line.c":
                ed_dda = edx
                holder_dda = h
                break
        app.notebook.select(holder_dda)
        root.update()
        active = app._current()
        check("tab switch moves current", active is ed_dda)
        check("statusbar follows tab switch",
              app.lbl_file.cget("text") == os.path.abspath(dda))
        check("Lines follows switched tab",
              app.lbl_lines.cget("text").startswith("Lines:"))

        app.close_tab(active)
        root.update()
        remaining = app._current()
        check("close one tab keeps status on remaining file",
              app.lbl_file.cget("text") == remaining.filepath)
        check("Lines still shown for remaining file",
              app.lbl_lines.cget("text").startswith("Lines:"))
        check("no stale Sel", app.lbl_sel.cget("text") == "Sel: 0")

        # ---- Compile Log tab sits beside Problems / Terminal ----
        tabs = [app.bottom.tab(i, "text") for i in app.bottom.tabs()]
        check("Compile Log tab present and ordered",
              tabs == ["Problems", "Compile Log", "Terminal"])

        step3()

    # ------------------------------------------------------------------
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="clite_test_statusbar_")
    bad = os.path.join(tmpdir, "tmp_status_bad.c")
    good = os.path.join(tmpdir, "tmp_status_good.c")

    def step3():
        with open(bad, "w") as f:
            f.write("int main() { return undeclared_name; }\n")
        app.open_file(bad)
        app.compile_current()
        root.after(500, step4)

    def step4():
        if app.build_busy:
            root.after(200, step4)
            return
        log = app.compilelog.text.get("1.0", "end")
        check("log shows compiler command", "gcc" in log)
        check("log shows compiler output", "undeclared_name" in log)
        check("log shows FAILED", "FAILED" in log)
        check("log tab auto-selected on failure",
              app.bottom.select() == str(app.compilelog))
        check("problems still parsed", any(
            p["severity"] == "error" for p in app.problems._items))
        step5()

    def step5():
        with open(good, "w") as f:
            f.write("int main(void) { return 0; }\n")
        app.open_file(good)
        app.compile_current()
        root.after(500, step6)

    def step6():
        if app.build_busy:
            root.after(200, step6)
            return
        log = app.compilelog.text.get("1.0", "end")
        check("success summary written", "successful" in log)

        for f in (bad, good):
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass
        app.on_close()
        root.destroy()

    # ------------------------------------------------------------------
    root.after(400, step1)
    root.mainloop()


main()
print("=== RESULTS ===")
ok = all(passed for _, passed in results)
for name, passed in results:
    print("%-52s %s" % (name, "PASS" if passed else "FAIL"))
sys.exit(0 if ok else 1)
