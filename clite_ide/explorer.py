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

# File type to icon mapping
FILE_TYPE_ICONS = {
    "c": "c",
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "h": "h",
    "hpp": "hpp",
    "py": "py",
    "js": "js",
    "ts": "ts",
    "html": "html",
    "css": "css",
    "json": "json",
    "md": "md",
    "txt": "txt",
    "xml": "xml",
    "csv": "csv",
    "folder": "folder",
    "folder_open": "folder_open",
    "default": "default",
}


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
        self._rename_entry = None    # inline rename entry widget
        self._rename_iid = None      # item being renamed
        self._rename_original = None # original name
        self._icons = {}             # file type -> PhotoImage

        self._make_fonts()
        self._make_toolbar()
        self._make_icons()

        self.tree = ttk.Treeview(self, show="tree", selectmode="browse",
                                 style="Explorer.Treeview")
        vs = ttk.Scrollbar(self, orient="vertical",
                           command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        vs.grid(row=1, column=1, sticky="ns")
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<Double-1>", self._on_activate)
        self.tree.bind("<Return>", self._on_enter)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<F2>", self._start_rename)
        self.tree.bind("<Delete>", self._delete_selected)
        self.tree.bind("<FocusIn>", self._on_focus_in)
        self.tree.bind("<FocusOut>", self._on_focus_out)

        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<Double-1>", self._on_activate)
        self.tree.bind("<Return>", self._on_enter)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<F2>", self._start_rename)
        self.tree.bind("<Delete>", self._delete_selected)
        self.tree.bind("<FocusIn>", self._on_focus_in)
        self.tree.bind("<FocusOut>", self._on_focus_out)

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

    def _make_toolbar(self):
        """Create the explorer toolbar with New File, New Folder, Refresh, Collapse All buttons."""
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        self.columnconfigure(0, weight=1)

        # Create toolbar icons (16x16)
        self._toolbar_icons = self._make_toolbar_icons()

        # New File button - document with plus
        btn_new_file = ttk.Button(toolbar, image=self._toolbar_icons["new_file"],
                                  command=self._new_file, width=2)
        btn_new_file.pack(side="left", padx=1)
        self._add_tooltip(btn_new_file, "New File (Ctrl+N)")

        # New Folder button - folder with plus
        btn_new_folder = ttk.Button(toolbar, image=self._toolbar_icons["new_folder"],
                                    command=self._new_folder, width=2)
        btn_new_folder.pack(side="left", padx=1)
        self._add_tooltip(btn_new_folder, "New Folder")

        # Refresh button - circular arrow
        btn_refresh = ttk.Button(toolbar, image=self._toolbar_icons["refresh"],
                                 command=self.refresh, width=2)
        btn_refresh.pack(side="left", padx=1)
        self._add_tooltip(btn_refresh, "Refresh")

        # Collapse All button - collapse/tree icon
        btn_collapse = ttk.Button(toolbar, image=self._toolbar_icons["collapse"],
                                  command=self._collapse_all, width=2)
        btn_collapse.pack(side="left", padx=1)
        self._add_tooltip(btn_collapse, "Collapse All")

        # Open Folder button - open folder icon
        btn_open_folder = ttk.Button(toolbar, image=self._toolbar_icons["open_folder"],
                                     command=self.app.open_folder_dialog, width=2)
        btn_open_folder.pack(side="left", padx=1)
        self._add_tooltip(btn_open_folder, "Open Folder")

    def _add_tooltip(self, widget, text):
        """Add a simple tooltip to a widget."""
        def show_tooltip(event):
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(tooltip, text=text, background="#ffffe0",
                              relief="solid", borderwidth=1, padding=(4, 2))
            label.pack()
            widget._tooltip = tooltip

        def hide_tooltip(event):
            if hasattr(widget, '_tooltip') and widget._tooltip:
                widget._tooltip.destroy()
                widget._tooltip = None

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

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
        self._make_icons()
        for iid in self.tree.get_children(""):
            self._update_item_image(iid)

    # ------------------------------------------------------------------
    #  icons
    # ------------------------------------------------------------------

    def _px(self, img, x, y, color):
        img.put(color, (x, y))

    def _make_icons(self):
        """Create all file type icons."""
        t = THEMES.get(self.app.settings.get("theme", "Light"), THEMES["Light"])
        folder_color = t["icon_folder"]
        file_color = t["icon_file"]

        # Folder icons
        self._icons["folder"] = self._make_folder_icon(folder_color, False)
        self._icons["folder_open"] = self._make_folder_icon(folder_color, True)

        # C/C++ file icons
        self._icons["c"] = self._make_file_icon("C", file_color, "#00599C")  # blue
        self._icons["cpp"] = self._make_file_icon("C++", file_color, "#00599C")
        self._icons["h"] = self._make_file_icon("H", file_color, "#F34B7D")  # pink
        self._icons["hpp"] = self._make_file_icon("H++", file_color, "#F34B7D")

        # Other common file type icons
        self._icons["py"] = self._make_file_icon("py", file_color, "#3776AB")
        self._icons["js"] = self._make_file_icon("JS", file_color, "#F7DF1E")
        self._icons["ts"] = self._make_file_icon("TS", file_color, "#3178C6")
        self._icons["html"] = self._make_file_icon("HTML", file_color, "#E34F26")
        self._icons["css"] = self._make_file_icon("CSS", file_color, "#1572B6")
        self._icons["json"] = self._make_file_icon("JSON", file_color, "#292929")
        self._icons["md"] = self._make_file_icon("MD", file_color, "#083FA1")
        self._icons["txt"] = self._make_file_icon("TXT", file_color, "#FFFFFF")
        self._icons["xml"] = self._make_file_icon("XML", file_color, "#F05032")
        self._icons["csv"] = self._make_file_icon("CSV", file_color, "#217346")

        # Default file icon
        self._icons["default"] = self._make_file_icon("", file_color, file_color)

    def _make_folder_icon(self, color, open_state):
        """Create a folder icon (12x12)."""
        img = tk.PhotoImage(width=12, height=12)
        px = self._px
        if open_state:
            # Open folder
            for x in range(3, 9):
                px(img, x, 1, color)
            for y in (2, 3):
                for x in range(2, 10):
                    px(img, x, y, color)
            for y in range(4, 11):
                for x in range(1, 11):
                    px(img, x, y, color)
        else:
            # Closed folder
            for x in range(3, 9):
                px(img, x, 2, color)
            for y in (3, 4):
                for x in range(2, 10):
                    px(img, x, y, color)
            for y in range(5, 11):
                for x in range(1, 11):
                    px(img, x, y, color)
        return img

    def _make_file_icon(self, text, bg_color, accent_color):
        """Create a file icon with optional text."""
        img = tk.PhotoImage(width=12, height=12)
        px = self._px
        # File shape
        for y in range(2, 11):
            for x in range(2, 10):
                px(img, x, y, bg_color)
        # Folded corner
        px(img, 8, 2, accent_color)
        px(img, 9, 2, accent_color)
        px(img, 9, 3, accent_color)
        # Text lines (simulated)
        for y in (5, 7, 9):
            for x in range(3, 9):
                px(img, x, y, accent_color if text else bg_color)
        return img

    def _make_toolbar_icons(self):
        """Create toolbar icons (16x16)."""
        t = THEMES.get(self.app.settings.get("theme", "Light"), THEMES["Light"])
        color = t["icon_folder"]
        icons = {}

        # New File - document with plus
        img = tk.PhotoImage(width=16, height=16)
        px = self._px
        # Document shape
        for y in range(2, 13):
            for x in range(2, 11):
                px(img, x, y, color)
        # Folded corner
        px(img, 9, 2, color)
        px(img, 10, 2, color)
        px(img, 10, 3, color)
        # Plus sign
        px(img, 7, 7, color)
        px(img, 8, 7, color)
        px(img, 9, 7, color)
        px(img, 8, 6, color)
        px(img, 8, 8, color)
        icons["new_file"] = img

        # New Folder - folder with plus
        img = tk.PhotoImage(width=16, height=16)
        # Folder base
        for x in range(3, 13):
            px(img, x, 3, color)
        for y in range(4, 7):
            for x in range(2, 14):
                px(img, x, y, color)
        for y in range(7, 14):
            for x in range(1, 14):
                px(img, x, y, color)
        # Plus sign
        px(img, 7, 9, color)
        px(img, 8, 9, color)
        px(img, 9, 9, color)
        px(img, 8, 8, color)
        px(img, 8, 10, color)
        icons["new_folder"] = img

        # Refresh - circular arrow
        img = tk.PhotoImage(width=16, height=16)
        # Circle with arrow
        for x in range(4, 12):
            px(img, x, 2, color)
            px(img, x, 13, color)
        for y in range(3, 13):
            px(img, 3, y, color)
            px(img, 12, y, color)
        # Arrow head
        px(img, 10, 2, color)
        px(img, 11, 3, color)
        px(img, 12, 4, color)
        px(img, 11, 4, color)
        px(img, 10, 5, color)
        icons["refresh"] = img

        # Collapse All - tree collapse
        img = tk.PhotoImage(width=16, height=16)
        # Tree lines
        for y in range(3, 14):
            px(img, 8, y, color)
        # Branches
        for x in range(3, 8):
            px(img, x, 6, color)
        for x in range(3, 8):
            px(img, x, 11, color)
        # Collapse arrows
        for y in range(4, 8):
            px(img, 10 - y + 3, y, color)
        for y in range(9, 13):
            px(img, 10 - y + 9, y, color)
        icons["collapse"] = img

        # Open Folder - folder with open arrow
        img = tk.PhotoImage(width=16, height=16)
        # Folder base (open state)
        for x in range(3, 13):
            px(img, x, 2, color)
        for y in range(3, 5):
            for x in range(2, 14):
                px(img, x, y, color)
        for y in range(5, 14):
            for x in range(1, 14):
                px(img, x, y, color)
        # Arrow pointing right/out (open)
        for y in range(7, 10):
            px(img, 5 + y - 7, y, color)
        for y in range(7, 10):
            px(img, 10 - (y - 7), y, color)
        icons["open_folder"] = img

        return icons

    def _get_file_icon(self, name):
        """Get the appropriate icon for a file based on extension."""
        if not name or "." not in name:
            return self._icons.get("default")
        ext = name.rsplit(".", 1)[-1].lower()
        return self._icons.get(ext, self._icons.get("default"))

    def _item_image(self, iid):
        base = self._base_tag.get(iid)
        path = self._path_by_iid.get(iid)
        if not path:
            return None
        if base == "folder":
            is_open = self.tree.item(iid, "open")
            return self._icons.get("folder_open" if is_open else "folder")
        if base in ("cfile", "file"):
            name = os.path.basename(path)
            return self._get_file_icon(name)
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
                               tags=("folder",), open=False)
        self._path_by_iid[iid] = path
        self._iid_by_path[path] = iid
        self._base_tag[iid] = "folder"
        self.tree.insert(iid, "end", text="", tags=("placeholder",))
        # Update icon after insertion
        self._update_item_image(iid)

    def _insert_file_node(self, parent, path, name):
        tag = ("cfile" if name.lower().endswith(C_EXTENSIONS)
               else "file")
        iid = self.tree.insert(parent, "end", text=name,
                               tags=(tag,))
        self._path_by_iid[iid] = path
        self._iid_by_path[path] = iid
        self._base_tag[iid] = tag
        # Update icon after insertion
        self._update_item_image(iid)

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

    def _rename_selected(self, event=None):
        """Rename selected item - uses inline rename."""
        self._start_rename()

    def _delete_selected(self, event=None):
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
    #  inline rename
    # ------------------------------------------------------------------

    def _start_rename(self, event=None):
        """Start inline rename for the selected item."""
        sel = self.tree.selection()
        if not sel:
            return
        self._rename_iid = sel[0]
        path = self._path_by_iid.get(self._rename_iid)
        if not path:
            return
        # Don't allow renaming the root
        if self.root_path and os.path.abspath(path) == os.path.abspath(self.root_path):
            return

        self._rename_original = os.path.basename(path)
        # Get the item's bounding box
        bbox = self.tree.bbox(self._rename_iid, column="#0")
        if not bbox:
            return
        x, y, width, height = bbox

        # Create entry widget for inline rename
        self._rename_entry = ttk.Entry(self.tree)
        self._rename_entry.place(x=x, y=y, width=width, height=height)
        self._rename_entry.insert(0, self._rename_original)
        self._rename_entry.select_range(0, tk.END)
        self._rename_entry.focus_set()

        # Bind events
        self._rename_entry.bind("<Return>", self._confirm_rename)
        self._rename_entry.bind("<Escape>", self._cancel_rename)
        self._rename_entry.bind("<FocusOut>", self._confirm_rename)

    def _confirm_rename(self, event=None):
        """Confirm the inline rename."""
        if not self._rename_entry or not self._rename_iid:
            return
        newname = self._rename_entry.get().strip()
        self._rename_entry.destroy()
        self._rename_entry = None

        if not newname or newname == self._rename_original:
            self._rename_iid = None
            self._rename_original = None
            self.tree.focus_set()
            return

        # Validate filename
        if not self._is_valid_filename(newname):
            dialogs.show_error(self, "Rename", "Invalid filename.")
            self._rename_iid = None
            self._rename_original = None
            self.tree.focus_set()
            return

        path = self._path_by_iid.get(self._rename_iid)
        if not path:
            self._rename_iid = None
            self._rename_original = None
            self.tree.focus_set()
            return

        newpath = os.path.join(os.path.dirname(path), newname)
        if os.path.exists(newpath):
            dialogs.show_error(self, "Rename", "A file or folder with that name already exists.")
            self._rename_iid = None
            self._rename_original = None
            self.tree.focus_set()
            return

        try:
            os.rename(path, newpath)
        except OSError as exc:
            dialogs.show_error(self, "Rename", str(exc))
            self._rename_iid = None
            self._rename_original = None
            self.tree.focus_set()
            return

        # Update open editors
        self.app.rename_editors(path, newpath)
        if self._active_path == os.path.abspath(path):
            self.set_active_file(newpath)

        self.refresh()
        self._rename_iid = None
        self._rename_original = None
        self.tree.focus_set()

    def _cancel_rename(self, event=None):
        """Cancel the inline rename."""
        if self._rename_entry:
            self._rename_entry.destroy()
            self._rename_entry = None
        self._rename_iid = None
        self._rename_original = None
        self.tree.focus_set()

    def _is_valid_filename(self, name):
        """Check if a filename is valid on Windows."""
        if not name:
            return False
        # Windows invalid characters
        invalid_chars = '<>:"/\\|?*'
        for ch in invalid_chars:
            if ch in name:
                return False
        # Reserved names (without extension)
        base = name.split('.')[0].upper()
        reserved = {"CON", "PRN", "AUX", "NUL",
                    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}
        if base in reserved:
            return False
        # Cannot end with space or dot
        if name.endswith(' ') or name.endswith('.'):
            return False
        return True

    def _collapse_all(self):
        """Collapse all expanded folders."""
        def collapse_item(iid):
            self.tree.item(iid, open=False)
            for child in self.tree.get_children(iid):
                collapse_item(child)

        for root_iid in self.tree.get_children(""):
            collapse_item(root_iid)

    def _on_focus_in(self, event):
        """Handle tree focus in."""
        pass

    def _on_focus_out(self, event):
        """Handle tree focus out - confirm any pending rename."""
        if self._rename_entry:
            self._confirm_rename()

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