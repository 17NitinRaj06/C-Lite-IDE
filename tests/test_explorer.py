import os
import shutil
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import clite_ide.explorer as exmod
from clite_ide.app import App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []


def check(name, ok):
    results.append((name, ok))
    print("%-52s %s" % (name, "PASS" if ok else "FAIL"))


def dump_text(ex):
    out = []
    for iid in ex.tree.get_children(""):
        out.append(ex.tree.item(iid, "text"))
    return out


def find_iid(ex, rel):
    path = os.path.normpath(os.path.join(ex.root_path, rel))
    return ex._iid_by_path.get(path)


def main():
    global root
    tmp = os.path.join(ROOT, "build", "tmp_explorer")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "include"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "build"), exist_ok=True)
    with open(os.path.join(tmp, "src", "main.c"), "w") as f:
        f.write("int main(){return 0;}\n")
    with open(os.path.join(tmp, "src", "util.cpp"), "w") as f:
        f.write("int f(){return 1;}\n")
    with open(os.path.join(tmp, "include", "graphics.h"), "w") as f:
        f.write("#pragma once\n")
    with open(os.path.join(tmp, "notes.txt"), "w") as f:
        f.write("x\n")
    with open(os.path.join(tmp, "build", "main.exe"), "w") as f:
        f.write("xx")

    root = tk.Tk()
    app = App(root)
    root.update()
    ex = app.explorer

    # ---- startup empty state ----
    check("startup shows No folder opened",
          dump_text(ex) == ["No folder opened"])

    # ---- set_root -> tree structure ----
    ex.set_root(tmp)
    root.update()
    root_iid = ex.tree.get_children("")[0]
    check("root node is the folder", ex.tree.item(root_iid, "text")
          == "tmp_explorer")
    check("root is folder-tagged",
          "folder" in ex.tree.item(root_iid, "tags"))

    top = sorted(ex.tree.item(c, "text")
                 for c in ex.tree.get_children(root_iid))
    check("top-level entries listed", top == ["include", "notes.txt", "src"])
    check("build dir skipped", "build" not in top)

    src_iid = find_iid(ex, "src")
    inc_iid = find_iid(ex, "include")
    check("folders have placeholders before open",
          ex.tree.get_children(src_iid) and
          ex.tree.get_children(inc_iid))
    check("folders lazy (not loaded yet)",
          src_iid not in ex._loaded and inc_iid not in ex._loaded)

    # ---- lazy load on open ----
    ex.tree.item(src_iid, open=True)
    ex._ensure_loaded(src_iid)
    root.update()
    kids = sorted(ex.tree.item(c, "text")
                  for c in ex.tree.get_children(src_iid))
    check("src children loaded on open", kids == ["main.c", "util.cpp"])
    tags = {ex.tree.item(c, "text"): ex.tree.item(c, "tags") for c in
            ex.tree.get_children(src_iid)}
    check("C/C++ files tagged cfile",
          tags.get("main.c") == ("cfile",) and
          tags.get("util.cpp") == ("cfile",))
    notes = find_iid(ex, "notes.txt")
    check("other files tagged file",
          ex.tree.item(notes, "tags") == ("file",))
    ex.tree.item(inc_iid, open=True)
    ex._ensure_loaded(inc_iid)
    h = find_iid(ex, "include/graphics.h")
    check("header tagged cfile",
          ex.tree.item(h, "tags") == ("cfile",))

    # ---- nested empty folder ----
    empty = os.path.join(tmp, "empty")
    os.makedirs(empty, exist_ok=True)
    ex.refresh()
    root.update()
    empty_iid = find_iid(ex, "empty")
    ex.tree.item(empty_iid, open=True)
    ex._ensure_loaded(empty_iid)
    check("nested empty folder opens to nothing",
          ex.tree.get_children(empty_iid) == ())

    # ---- empty root folder message ----
    empty_root = os.path.join(ROOT, "build", "tmp_explorer_empty")
    shutil.rmtree(empty_root, ignore_errors=True)
    os.makedirs(empty_root, exist_ok=True)
    ex.set_root(empty_root)
    root.update()
    er_iid = ex.tree.get_children("")[0]
    er_kids = ex.tree.get_children(er_iid)
    check("empty project folder shows message",
          er_kids and ex.tree.item(er_kids[0], "text") == "(empty folder)")
    ex.set_root(tmp)
    root.update()
    src_iid = find_iid(ex, "src")
    ex.tree.item(src_iid, open=True)
    ex._ensure_loaded(src_iid)

    # ---- double-click opens file / folder toggles ----
    main_iid = find_iid(ex, "src/main.c")
    ex.tree.selection_set(main_iid)
    ex._handle_item(main_iid)
    root.update()
    ed = app._current()
    check("double-click opens file tab",
          ed is not None and
          ed.filepath == os.path.normpath(os.path.join(tmp, "src/main.c")))
    n_tabs = len(app.notebook.tabs())
    ex._handle_item(main_iid)
    root.update()
    check("double-click on open file reuses tab",
          len(app.notebook.tabs()) == n_tabs)
    check("active file highlighted",
          ex._active_iids == {main_iid} and
          "active" in ex.tree.item(main_iid, "tags"))
    ex.tree.item(src_iid, open=True)
    ex._handle_item(src_iid)
    root.update()
    check("double-click folder collapses",
          not ex.tree.item(src_iid, "open"))

    # ---- active file follows tab switch ----
    app.open_file(os.path.join(tmp, "include", "graphics.h"))
    root.update()
    h_iid = find_iid(ex, "include/graphics.h")
    check("active file follows open", ex._active_iids == {h_iid})
    app.notebook.select(app._tab_for_editor(ed))
    root.update()
    check("active file follows tab switch", ex._active_iids == {main_iid})

    # ---- context menu: New File / New Folder ----
    orig_ask = exmod.dialogs.ask_string
    orig_yesno = exmod.dialogs.ask_yes_no
    exmod.dialogs.ask_string = lambda *a, **k: "newfile.c"
    src_iid = find_iid(ex, "src")
    ex.tree.selection_set(src_iid)
    ex._new_file()
    root.update()
    check("New File creates + opens",
          os.path.isfile(os.path.join(tmp, "src", "newfile.c")) and
          app._current().filepath ==
          os.path.join(tmp, "src", "newfile.c"))
    src_iid = find_iid(ex, "src")
    ex.tree.selection_set(src_iid)
    exmod.dialogs.ask_string = lambda *a, **k: "newdir"
    ex._new_folder()
    root.update()
    check("New Folder creates",
          os.path.isdir(os.path.join(tmp, "src", "newdir")))

    # ---- context menu: Rename updates editor ----
    exmod.dialogs.ask_string = lambda *a, **k: "renamed.c"
    ex.tree.selection_set(find_iid(ex, "src/newfile.c"))
    ex._rename_selected()
    root.update()
    renamed = os.path.join(tmp, "src", "renamed.c")
    check("Rename moved file",
          os.path.isfile(renamed) and
          not os.path.isfile(os.path.join(tmp, "src", "newfile.c")))
    check("Rename updated open editor",
          app._current().filepath == renamed)
    check("Rename re-highlighted active file",
          ex._active_path == renamed)

    # ---- context menu: Delete closes editor ----
    exmod.dialogs.ask_yes_no = lambda *a, **k: True
    exmod.dialogs.ask_string = orig_ask
    ex.tree.selection_set(find_iid(ex, "src/renamed.c"))
    ex._delete_selected()
    root.update()
    check("Delete removed file", not os.path.exists(renamed))
    check("Delete closed its editor tab",
          all(getattr(app.notebook.nametowidget(t), "editor", None)
              .filepath != renamed
              for t in app.notebook.tabs()))
    ex.tree.selection_set(find_iid(ex, "src/newdir"))
    ex._delete_selected()
    root.update()
    check("Delete removed folder",
          not os.path.isdir(os.path.join(tmp, "src", "newdir")))

    # ---- auto-sync picks up external changes ----
    external = os.path.join(tmp, "external.c")
    with open(external, "w") as f:
        f.write("int z(){return 9;}\n")
    ex._auto_sync()
    root.update()
    check("auto-sync shows external file",
          find_iid(ex, "external.c") is not None)
    os.remove(external)
    ex._auto_sync()
    root.update()
    check("auto-sync removes deleted file",
          find_iid(ex, "external.c") is None)

    # ---- open folder switches the tree to the new folder ----
    app.explorer.set_root(os.path.join(ROOT, "examples"))
    root.update()
    check("set_root switches tree to new folder",
          ex.tree.get_children("") and
          ex.tree.item(ex.tree.get_children("")[0], "text") == "examples")

    exmod.dialogs.ask_yes_no = orig_yesno
    exmod.dialogs.ask_string = orig_ask
    app.on_close()
    root.destroy()
    shutil.rmtree(tmp, ignore_errors=True)


main()
print("=== RESULTS ===")
ok = all(passed for _, passed in results)
for name, passed in results:
    print("%-52s %s" % (name, "PASS" if passed else "FAIL"))
sys.exit(0 if ok else 1)