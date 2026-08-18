"""Project / file explorer sidebar.

Shows the currently opened folder (or project directory) as a lazy-loaded
file tree with expand/collapse arrows, context-menu file management, live
active-file highlighting, and automatic filesystem sync.
"""

import os
import shutil
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from . import dialogs
from .settings import THEMES
from .uistyle import style_menu

C_EXTENSIONS = (".c", ".cpp", ".cc", ".cxx", ".c++", ".h", ".hpp")


class Explorer(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.root_path = None        # displayed root directory (abs path)
        self._iid_by_path = {}       # abs path -> tree item id
        self._path_by_iid = {}       # tree item id -> abs path
        self._loaded = set()         # item ids whose children are loaded
        self._base_tag = {}          # item id -> folder/cfile/file tag
        self._active_path = None     # file currently highlighted
        self._active_iids = set()
        self._last_snap = None

        self._make_fonts()

        self.tree = ttk.Treeview(self, show="tree", selectmode="browse",
                                 style="Explorer.Treeview")
        vs = ttk.Scrollbar(self, orient="vertical",
                           command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<Double-1>", self._on_activate)
        self.tree.bind("<Return>", self._on_enter)
        self.tree.bind("<Button-3>", self._on_right_click)

        self._menu = None
        self.apply_theme(app.settings.get("theme", "Light"))
        self.refresh()
        self._schedule_sync()

    # ------------------------------------------------------------------

    def _make_fonts(self):
        base = tkfont.nametofont("TkDefaultFont")
        self._fold_font = base.copy()
        self._fold_font.configure(weight="bold")
        self._dim_font = base.copy()
        self._dim_font.configure(slant="italic")

    def apply_theme(self, theme_name):
        t = THEMES.get(theme_name, THEMES["Light"])
        self.tree.tag_configure("folder",
                                foreground=t["panel_fg"],
                                font=self._fold_font)
        self.tree.tag_configure("cfile", foreground=t["editor_fg"])
        self.tree.tag_configure("file", foreground=t["gutter_fg"])
        self.tree.tag_configure("active", foreground=t["status_run"])
        self.tree.tag_configure("dim", foreground=t["gutter_fg"],
                                font=self._dim_font)
        self._folder_img = self._make_icon("folder", t["icon_folder"])
        self._file_img = self._make_icon("file", t["icon_file"])
        for iid in self.tree.get_children(""):
            self._update_item_image(iid)

    # ------------------------------------------------------------------
    #  icons
    # ------------------------------------------------------------------

    def _px(self, img, x, y, color):
        img.put(color, (x, y))

    def _make_icon(self, kind, color):
        img = tk.PhotoImage(width=12, height=12)
        px = self._px
        if kind == "folder":
            for x in range(3, 9):
                px(img, x, 2, color)
            for y in (3, 4):
                for x in range(2, 10):
                    px(img, x, y, color)
            for y in range(5, 11):
                for x in range(1, 11):
                    px(img, x, y, color)
        else:
            for y in range(2, 11):
                for x in range(2, 10):
                    px(img, x, y, color)
            px(img, 8, 2, color)
            px(img, 9, 2, color)
            px(img, 9, 3, color)
            for y in (5, 7, 9):
                for x in range(3, 9):
                    px(img, x, y, color)
        return img

    def _item_image(self, iid):
        base = self._base_tag.get(iid)
        if base == "folder":
            return self._folder_img
        if base in ("cfile", "file"):
            return self._file_img
        return None

    def _update_item_image(self, iid):
        img = self._item_image(iid)
        name = str(img) if img else ""
        if self.tree.item(iid, "image") != name:
            self.tree.item(iid, image=name)
        for child in self.tree.get_children(iid):
            self._update_item_image(child)

    # ------------------------------------------------------------------
    #  root / project
    # ------------------------------------------------------------------

    def set_root(self, path):
        self.root_path = os.path.abspath(path) if path else None
        self.refresh()
        self._schedule_sync()

    def set_project(self, project):
        self.set_root(project.directory if project else None)

    # ------------------------------------------------------------------
    #  tree building (lazy)
    # ------------------------------------------------------------------

    def refresh(self):
        open_paths = set()
        for iid, path in self._path_by_iid.items():
            if os.path.isdir(path) and self.tree.item(iid, "open"):
                open_paths.add(os.path.abspath(path))

        self.tree.delete(*self.tree.get_children())
        self._iid_by_path.clear()
        self._path_by_iid.clear()
        self._loaded.clear()
        self._base_tag.clear()

        if not self.root_path:
            self.tree.insert("", "end", text="No folder opened",
                             tags=("dim",))
            self._last_snap = None
            return

        root = os.path.abspath(self.root_path)
        riid = self.tree.insert("", "end",
                                text=os.path.basename(root) or root,
                                tags=("folder",), open=True)
        self._iid_by_path[root] = riid
        self._path_by_iid[riid] = root
        self._base_tag[riid] = "folder"
        self._load_children(riid, root)
        self._loaded.add(riid)

        for p in open_paths:
            iid = self._iid_by_path.get(p)
            if iid is not None:
                self.tree.item(iid, open=True)
                self._ensure_loaded(iid)

        if not self.tree.get_children(riid):
            self.tree.insert(riid, "end", text="(empty folder)",
                             tags=("dim",))

        self._last_snap = self._snapshot(root)
        self._apply_active()

    def _snapshot(self, root):
        """Set of absolute paths under root (structure only, build skipped)."""
        snap = set()
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "build"]
            for name in dirnames:
                snap.add(os.path.join(dirpath, name))
            for name in filenames:
                snap.add(os.path.join(dirpath, name))
        return snap

    def _insert_dir_node(self, parent, path):
        iid = self.tree.insert(parent, "end",
                               text=os.path.basename(path) or path,
                               image=self._folder_img,
                               tags=("folder",), open=False)
        self._path_by_iid[iid] = path
        self._iid_by_path[path] = iid
        self._base_tag[iid] = "folder"
        self.tree.insert(iid, "end", text="", tags=("placeholder",))

    def _insert_file_node(self, parent, path, name):
        tag = ("cfile" if name.lower().endswith(C_EXTENSIONS)
               else "file")
        iid = self.tree.insert(parent, "end", text=name,
                               image=self._file_img, tags=(tag,))
        self._path_by_iid[iid] = path
        self._iid_by_path[path] = iid
        self._base_tag[iid] = tag

    def _load_children(self, parent_iid, dir_path):
        for child in self.tree.get_children(parent_iid):
            if child not in self._path_by_iid:
                self.tree.delete(child)
        try:
            entries = sorted(os.listdir(dir_path), key=str.lower)
        except OSError:
            return
        for name in entries:
            if name == "build":
                continue
            full = os.path.join(dir_path, name)
            if os.path.isdir(full):
                self._insert_dir_node(parent_iid, full)
            else:
                self._insert_file_node(parent_iid, full, name)

    def _ensure_loaded(self, iid):
        path = self._path_by_iid.get(iid)
        if path and os.path.isdir(path) and iid not in self._loaded:
            self._load_children(iid, path)
            self._loaded.add(iid)

    def _on_open(self, event):
        self._ensure_loaded(self.tree.focus())

    # ------------------------------------------------------------------
    #  active file highlighting
    # ------------------------------------------------------------------

    def set_active_file(self, path):
        self._active_path = os.path.abspath(path) if path else None
        self._apply_active()

    def _apply_active(self):
        for iid in self._active_iids:
            base = self._base_tag.get(iid)
            if base:
                self.tree.item(iid, tags=(base,))
        self._active_iids = set()
        if not self._active_path or not self.root_path:
            return
        iid = self._reveal(self._active_path)
        if iid:
            base = self._base_tag.get(iid, "file")
            self.tree.item(iid, tags=(base, "active"))
            self._active_iids.add(iid)
            try:
                self.tree.see(iid)
            except tk.TclError:
                pass

    def _reveal(self, path):
        root = os.path.abspath(self.root_path)
        if not (path == root or path.startswith(root + os.sep)):
            return None
        riid = self._iid_by_path.get(root)
        if riid is None:
            return None
        self.tree.item(riid, open=True)
        if path == root:
            return riid
        rel = os.path.relpath(path, root)
        cur_dir = root
        for part in rel.split(os.sep)[:-1]:
            cur_dir = os.path.join(cur_dir, part)
            diid = self._iid_by_path.get(cur_dir)
            if diid is None:
                return None
            if diid not in self._loaded:
                self._load_children(diid, cur_dir)
                self._loaded.add(diid)
            self.tree.item(diid, open=True)
        return self._iid_by_path.get(path)

    # ------------------------------------------------------------------
    #  activation
    # ------------------------------------------------------------------

    def _handle_item(self, iid):
        if not iid:
            return
        path = self._path_by_iid.get(iid)
        if not path:
            return
        if os.path.isdir(path):
            self._toggle_dir(iid)
        else:
            self.app.open_file(path)

    def _toggle_dir(self, iid):
        if self.tree.item(iid, "open"):
            self.tree.item(iid, open=False)
        else:
            self.tree.item(iid, open=True)
            self._ensure_loaded(iid)

    def _on_activate(self, event):
        self._handle_item(self.tree.identify_row(event.y))

    def _on_enter(self, event):
        self._handle_item(self.tree.focus())

    def _open_selected(self):
        sel = self.tree.selection()
        if sel:
            self._handle_item(sel[0])

    # ------------------------------------------------------------------
    #  context menu
    # ------------------------------------------------------------------

    def _on_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        menu = tk.Menu(self, tearoff=0)
        if iid:
            self.tree.selection_set(iid)
            path = self._path_by_iid.get(iid)
            if path and os.path.isdir(path):
                menu.add_command(label="Open/Expand",
                                 command=lambda: self._toggle_dir(iid))
                menu.add_separator()
                menu.add_command(label="New File", command=self._new_file)
                menu.add_command(label="New Folder", command=self._new_folder)
                menu.add_separator()
                menu.add_command(label="Rename",
                                 command=self._rename_selected)
                menu.add_command(label="Delete",
                                 command=self._delete_selected)
            elif path:
                menu.add_command(label="Open", command=self._open_selected)
                menu.add_separator()
                menu.add_command(label="Rename",
                                 command=self._rename_selected)
                menu.add_command(label="Delete",
                                 command=self._delete_selected)
        else:
            menu.add_command(label="New File", command=self._new_file)
            menu.add_command(label="New Folder", command=self._new_folder)
        menu.add_separator()
        menu.add_command(label="Refresh Explorer", command=self.refresh)
        menu.add_command(label="Reveal in Explorer",
                         command=self._reveal_selected)
        style_menu(menu, THEMES.get(self.app.settings.get("theme", "Light"),
                                    THEMES["Light"]))
        self._menu = menu
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ------------------------------------------------------------------
    #  context menu actions
    # ------------------------------------------------------------------

    def _target_dir(self):
        sel = self.tree.selection()
        if sel:
            p = self._path_by_iid.get(sel[0])
            if p:
                return p if os.path.isdir(p) else os.path.dirname(p)
        return self.root_path

    def _new_file(self):
        target = self._target_dir()
        if not target:
            return
        name = dialogs.ask_string(self, "New File", "File name:")
        if not name:
            return
        if os.path.sep in name or "/" in name:
            dialogs.show_warning(self, "C-Lite", "Enter a file name only.")
            return
        full = os.path.join(target, name)
        if os.path.exists(full):
            dialogs.show_warning(self, "C-Lite", "File already exists.")
            return
        try:
            with open(full, "w", encoding="utf-8", newline="\n"):
                pass
        except OSError as exc:
            dialogs.show_error(self, "New File", str(exc))
            return
        self.refresh()
        self.app.open_file(full)

    def _new_folder(self):
        target = self._target_dir()
        if not target:
            return
        name = dialogs.ask_string(self, "New Folder", "Folder name:")
        if not name:
            return
        if os.path.sep in name or "/" in name:
            dialogs.show_warning(self, "C-Lite", "Enter a folder name only.")
            return
        full = os.path.join(target, name)
        if os.path.exists(full):
            dialogs.show_warning(self, "C-Lite", "Folder already exists.")
            return
        try:
            os.makedirs(full)
        except OSError as exc:
            dialogs.show_error(self, "New Folder", str(exc))
            return
        self.refresh()

    def _rename_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        path = self._path_by_iid.get(sel[0])
        if not path:
            return
        newname = dialogs.ask_string(
            self, "Rename", "New name:",
            initial=os.path.basename(path))
        if not newname or newname == os.path.basename(path):
            return
        newpath = os.path.join(os.path.dirname(path), newname)
        try:
            os.rename(path, newpath)
        except OSError as exc:
            dialogs.show_error(self, "Rename", str(exc))
            return
        self.app.rename_editors(path, newpath)
        if self._active_path == os.path.abspath(path):
            self.set_active_file(newpath)
        self.refresh()

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        path = self._path_by_iid.get(sel[0])
        if not path:
            return
        if not dialogs.ask_yes_no(self, "Delete",
                                   "Delete %s?"
                                   % os.path.basename(path)):
            return
        was_dir = os.path.isdir(path)
        try:
            if was_dir:
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError as exc:
            dialogs.show_error(self, "Delete", str(exc))
            return
        self.app.close_editor_for(path, was_dir)
        ap = self._active_path
        if ap and (ap == os.path.abspath(path) or
                   (was_dir and ap.startswith(os.path.abspath(path)
                                              + os.sep))):
            self.set_active_file(None)
        self.refresh()

    def _reveal_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        path = self._path_by_iid.get(sel[0])
        if not path:
            return
        try:
            os.startfile(os.path.dirname(path) if os.path.isfile(path)
                         else path)
        except OSError:
            pass

    # ------------------------------------------------------------------
    #  filesystem sync
    # ------------------------------------------------------------------

    def _schedule_sync(self):
        try:
            self._sync_job = self.app.root.after(2000, self._auto_sync)
        except tk.TclError:
            pass

    def _auto_sync(self):
        if not self.root_path:
            return
        try:
            if self.winfo_exists() and \
                    self._snapshot(self.root_path) != self._last_snap:
                self.refresh()
            self._schedule_sync()
        except (tk.TclError, OSError):
            try:
                self._schedule_sync()
            except tk.TclError:
                pass