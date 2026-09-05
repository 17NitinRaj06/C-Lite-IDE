"""C-Lite IDE main application window."""

import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk

from . import APP_NAME, APP_VERSION, USER_DATA_DIR, dialogs
from .builder import Builder
from .compilelog import CompileLog
from .dpi import enable_dpi_awareness
from .editor import Editor, FindBar
from .examples import list_examples
from .explorer import Explorer
from .problems import Problems
from .project import Project, create_project
from .runner import Runner
from .settings import (THEMES, Settings, compiler_source, find_gcc,
                       gcc_version)
from .tabs import ClosableNotebook
from .terminal import Terminal
from .uistyle import style_menu
from .windows import icon_path, set_app_user_model_id

MENU_SHORTCUTS = [
    ("Ctrl+N", "New File"),
    ("Ctrl+O", "Open File"),
    ("Ctrl+S", "Save"),
    ("Ctrl+Shift+S", "Save As"),
    ("F6", "Compile"),
    ("F5", "Compile & Run"),
    ("Shift+F5", "Stop"),
    ("Ctrl+F", "Find"),
    ("Ctrl+H", "Replace"),
    ("Ctrl+G", "Go to Line"),
    ("Ctrl+Z", "Undo"),
    ("Ctrl+Y", "Redo"),
    ("Ctrl+W", "Close Tab"),
]


class App:
    def __init__(self, root, startup_files=None):
        self.root = root
        self.settings = Settings()
        self.project = None
        self.project_root = None
        self.current = None
        self.running = False
        self.build_busy = False

        self.builder = Builder(self)
        self.runner = Runner(self)

        root.title("%s %s" % (APP_NAME, APP_VERSION))
        root.geometry("1024x680")
        root.minsize(760, 480)

        self._menus = []
        self._build_styles()
        self._build_layout()

        self.problems = Problems(self.bottom, self.settings,
                                 on_navigate=self.navigate)
        self.bottom.add(self.problems, text="Problems")
        self.compilelog = CompileLog(self.bottom, self.settings)
        self.bottom.add(self.compilelog, text="Compile Log")
        self.terminal = Terminal(self.bottom, self.settings,
                                 on_input=self.runner.write_stdin)
        self.bottom.add(self.terminal, text="Terminal")
        self.bottom.select(self.terminal)

        self._build_menu()
        self._build_toolbar()
        self._build_statusbar()
        self._bind_shortcuts()

        self.apply_theme(self.settings.get("theme", "Light"))

        self.notebook.bind("<<NotebookTabChanged>>",
                           self._on_notebook_tab_changed)
        self._update_compiler_status()

        # Open files passed on the command line, or fall back to a
        # blank tab if none were provided or all failed validation.
        opened = self._open_startup_files(startup_files)
        if not opened:
            self.new_file()
        self._update_title()

    # ------------------------------------------------------------------
    #  startup file handling
    # ------------------------------------------------------------------

    def _open_startup_files(self, paths):
        """Open each path from sys.argv in a new tab.  Returns True if
        at least one file was opened successfully.  Shows an error
        dialog for each path that doesn't exist."""
        if not paths:
            return False
        opened_any = False
        for path in paths:
            path = os.path.abspath(path)
            if not os.path.isfile(path):
                dialogs.show_error(
                    self.root, "Open",
                    "File not found:\n%s" % path)
                continue
            ed = self.open_file(path)
            if ed:
                opened_any = True
        return opened_any

    # ------------------------------------------------------------------
    #  construction helpers
    # ------------------------------------------------------------------

    def _build_styles(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

    def _build_menu(self):
        m = tk.Menu(self.root)
        self._menus.append(m)
        self.root.config(menu=m)

        file_menu = tk.Menu(m, tearoff=0)
        self._menus.append(file_menu)
        file_menu.add_command(label="New File", accelerator="Ctrl+N",
                              command=self.new_file)
        file_menu.add_command(label="Open File...", accelerator="Ctrl+O",
                              command=self.open_dialog)
        file_menu.add_command(label="Open Folder...",
                              command=self.open_folder_dialog)
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        self._menus.append(self.recent_menu)
        file_menu.add_cascade(label="Open Recent", menu=self.recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="New C Project...",
                              command=self.new_project_dialog)
        file_menu.add_command(label="Open C Project...",
                              command=self.open_project_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S",
                              command=self.save_current)
        file_menu.add_command(label="Save As...",
                              accelerator="Ctrl+Shift+S",
                              command=self.save_as_current)
        file_menu.add_command(label="Close Tab", accelerator="Ctrl+W",
                              command=self.close_current_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Examples...", command=self.show_examples)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        m.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(m, tearoff=0)
        self._menus.append(edit_menu)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z",
                              command=lambda: self._invoke_edit("undo"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y",
                              command=lambda: self._invoke_edit("redo"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut",
                              command=lambda: self._invoke_edit("cut"))
        edit_menu.add_command(label="Copy",
                              command=lambda: self._invoke_edit("copy"))
        edit_menu.add_command(label="Paste",
                              command=lambda: self._invoke_edit("paste"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Find...", accelerator="Ctrl+F",
                              command=self.show_find)
        edit_menu.add_command(label="Replace...", accelerator="Ctrl+H",
                              command=self.show_replace)
        edit_menu.add_command(label="Go to Line...", accelerator="Ctrl+G",
                              command=self.go_to_line)
        edit_menu.add_separator()
        edit_menu.add_command(label="Fold All",
                              command=lambda: self._edit_method("fold_all"))
        edit_menu.add_command(label="Unfold All",
                              command=lambda: self._edit_method("unfold_all"))
        m.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(m, tearoff=0)
        self._menus.append(view_menu)
        self.theme_menu = tk.Menu(view_menu, tearoff=0)
        self._menus.append(self.theme_menu)
        for name in THEMES:
            self.theme_menu.add_command(label=name,
                                        command=lambda n=name: self.set_theme(n))
        view_menu.add_cascade(label="Theme", menu=self.theme_menu)
        view_menu.add_command(label="Settings...", command=self.show_settings)
        m.add_cascade(label="View", menu=view_menu)

        build_menu = tk.Menu(m, tearoff=0)
        self._menus.append(build_menu)
        build_menu.add_command(label="Compile", accelerator="F6",
                               command=self.compile_current)
        build_menu.add_command(label="Compile & Run", accelerator="F5",
                               command=self.run_current)
        build_menu.add_command(label="Stop Program", accelerator="Shift+F5",
                               command=self.stop_current)
        build_menu.add_separator()
        build_menu.add_command(label="Clear Problems",
                               command=self.problems.clear)
        m.add_cascade(label="Build", menu=build_menu)

        run_menu = tk.Menu(m, tearoff=0)
        self._menus.append(run_menu)
        run_menu.add_command(label="Run", command=self.run_current)
        run_menu.add_command(label="Stop", command=self.stop_current)
        m.add_cascade(label="Run", menu=run_menu)

        help_menu = tk.Menu(m, tearoff=0)
        self._menus.append(help_menu)
        help_menu.add_command(label="Keyboard Shortcuts",
                              command=self.show_shortcuts)
        help_menu.add_command(label="Check for Updates",
                              command=self.check_for_updates)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        m.add_cascade(label="Help", menu=help_menu)

    def _build_toolbar(self):
        bar = ttk.Frame(self.root, padding=(4, 3))
        self.tb_new = ttk.Button(bar, text="New", width=7,
                                 command=self.new_file)
        self.tb_open = ttk.Button(bar, text="Open", width=7,
                                  command=self.open_dialog)
        self.tb_save = ttk.Button(bar, text="Save", width=7,
                                  command=self.save_current)
        self.tb_compile = ttk.Button(bar, text="Compile", width=9,
                                     command=self.compile_current)
        self.tb_run = ttk.Button(bar, text="Run", width=7,
                                 command=self.run_current)
        self.tb_stop = ttk.Button(bar, text="Stop", width=7,
                                  command=self.stop_current, state="disabled")
        for b in (self.tb_new, self.tb_open, self.tb_save):
            b.grid(row=0, column=len(bar.grid_slaves(0)), padx=2)
        ttk.Separator(bar, orient="vertical").grid(row=0, column=8,
                                                   sticky="ns", padx=6)
        self.tb_compile.grid(row=0, column=9, padx=2)
        self.tb_run.grid(row=0, column=10, padx=2)
        self.tb_stop.grid(row=0, column=11, padx=2)
        self.tb_sep = ttk.Separator(self.root, orient="horizontal")
        self.tb_sep.pack(side="top", fill="x")
        bar.pack(side="top", fill="x")

    def _build_layout(self):
        self.main_pane = ttk.Panedwindow(self.root, orient="horizontal")
        self.main_pane.pack(fill="both", expand=True)

        self.explorer = Explorer(self.main_pane, self)
        self.main_pane.add(self.explorer, weight=0)

        right = ttk.Frame(self.main_pane)
        self.main_pane.add(right, weight=1)

        self.vsplit = ttk.Panedwindow(right, orient="vertical")
        self.vsplit.pack(fill="both", expand=True)
        self.vsplit.bind("<Map>", self._on_vsplit_mapped)

        self.notebook = ClosableNotebook(self.vsplit,
                                         on_close_tab=self._close_tab_by_tab)
        self.vsplit.add(self.notebook, weight=3)
        self.notebook.bind("<Button-3>", self._tab_context_menu)

        self.bottom = ttk.Notebook(self.vsplit)
        self.bottom.configure(height=180)
        self.vsplit.add(self.bottom, weight=1)

        self._tab_menu = tk.Menu(self.root, tearoff=0)
        self._menus.append(self._tab_menu)
        self._tab_menu.add_command(label="Close Tab",
                                   command=self.close_current_tab)
        self._tab_menu.add_command(label="Close Others",
                                   command=self._close_other_tabs)

    def _build_statusbar(self):
        self.status = ttk.Frame(self.root, padding=(6, 2))
        self.lbl_file = ttk.Label(self.status, text="")
        self.lbl_pos = ttk.Label(self.status, text="",
                                 style="Muted.TLabel")
        self.lbl_sel = ttk.Label(self.status, text="Sel: 0",
                                 style="Muted.TLabel")
        self.lbl_lines = ttk.Label(self.status, text="",
                                   style="Muted.TLabel")
        self.lbl_gcc = ttk.Label(self.status, text="",
                                 style="Muted.TLabel")
        self.lbl_theme = ttk.Label(self.status, text="",
                                   style="Muted.TLabel")
        self.lbl_file.grid(row=0, column=0, sticky="w")
        self.lbl_pos.grid(row=0, column=1, padx=12)
        self.lbl_sel.grid(row=0, column=2, padx=12)
        self.lbl_lines.grid(row=0, column=3, padx=12)
        self.lbl_gcc.grid(row=0, column=4, padx=12, sticky="e")
        self.lbl_theme.grid(row=0, column=5, padx=12, sticky="e")
        self.status.columnconfigure(0, weight=1)
        self.status_sep = ttk.Separator(self.root, orient="horizontal")
        self.status_sep.pack(side="bottom", fill="x")
        self.status.pack(side="bottom", fill="x")

    def _bind_shortcuts(self):
        b = self.root.bind_all
        b("<Control-n>", lambda e: (self.new_file(), "break")[1])
        b("<Control-N>", lambda e: (self.new_file(), "break")[1])
        b("<Control-o>", lambda e: (self.open_dialog(), "break")[1])
        b("<Control-O>", lambda e: (self.open_dialog(), "break")[1])
        b("<Control-s>", lambda e: (self.save_current(), "break")[1])
        b("<Control-S>", lambda e: (self.save_current(), "break")[1])
        b("<Control-Shift-s>", lambda e: (self.save_as_current(), "break")[1])
        b("<Control-Shift-S>", lambda e: (self.save_as_current(), "break")[1])
        b("<Control-f>", lambda e: (self.show_find(), "break")[1])
        b("<Control-F>", lambda e: (self.show_find(), "break")[1])
        b("<Control-h>", lambda e: (self.show_replace(), "break")[1])
        b("<Control-H>", lambda e: (self.show_replace(), "break")[1])
        b("<Control-g>", lambda e: (self.go_to_line(), "break")[1])
        b("<Control-G>", lambda e: (self.go_to_line(), "break")[1])
        b("<Control-w>", lambda e: (self.close_current_tab(), "break")[1])
        b("<Control-W>", lambda e: (self.close_current_tab(), "break")[1])
        b("<F5>", lambda e: (self.run_current(), "break")[1])
        b("<F6>", lambda e: (self.compile_current(), "break")[1])
        b("<Shift-F5>", lambda e: (self.stop_current(), "break")[1])

    # ------------------------------------------------------------------
    #  editor tabs
    # ------------------------------------------------------------------

    def _make_editor(self, filepath=None):
        holder = ttk.Frame(self.notebook)
        ed = Editor(holder, self.settings,
                    on_dirty=self._on_editor_dirty,
                    on_cursor=self._on_cursor)
        fb = FindBar(holder, ed)
        ed.pack(fill="both", expand=True)
        fb.pack(fill="x")
        fb.grid_remove()
        holder.editor = ed
        holder.findbar = fb
        name = ed.display_name()
        tab = self.notebook.add_tab(holder, name, padding=0)
        self.notebook.select(holder)
        return ed

    def new_file(self):
        ed = self._make_editor()
        ed.set_text("")
        self._set_current(ed)
        self._update_title()

    def open_file(self, path):
        path = os.path.abspath(path)
        for holder in self.notebook.tabs():
            frame = self.notebook.nametowidget(holder)
            if getattr(frame, "editor", None) and \
                    frame.editor.filepath == path:
                self.notebook.select(frame)
                frame.editor.focus()
                self.explorer.set_active_file(path)
                return frame.editor
        if not os.path.isfile(path):
            return None
        ed = self._make_editor(path)
        try:
            ed.load_file(path)
        except OSError as exc:
            dialogs.show_error(self.root, "Open", str(exc))
            self.close_tab(ed)
            return None
        self._set_current(ed)
        self.settings.add_recent(path)
        self._update_recent_menu()
        self.explorer.set_active_file(path)
        self._update_title()
        return ed

    def open_dialog(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="Open Source File",
            filetypes=[("C source", "*.c"), ("C++ source",
                       "*.cpp *.cc *.cxx *.c++"),
                       ("C/C++ source", "*.c *.h *.cpp *.cc *.cxx *.c++"),
                       ("All files", "*.*")])
        if path:
            self.open_file(path)

    def _set_current(self, ed):
        self.current = ed
        self._update_title()

    def _current(self):
        if self.current is not None and self.current.winfo_exists():
            return self.current
        tabs = self.notebook.tabs()
        if tabs:
            frame = self.notebook.nametowidget(self.notebook.select())
            ed = getattr(frame, "editor", None)
            if ed:
                self.current = ed
                return ed
        return None

    def _on_notebook_tab_changed(self, event=None):
        """Keep the active-file state in sync when the user switches tabs."""
        sel = self.notebook.select()
        if not sel:
            self.current = None
        else:
            frame = self.notebook.nametowidget(sel)
            self.current = getattr(frame, "editor", None)
        ed = self.current
        self.explorer.set_active_file(
            ed.filepath if ed and ed.filepath else None)
        self._update_title()

    def _on_vsplit_mapped(self, event=None):
        """Once the editor/bottom split is really on screen, set a sensible
        default sash position so the bottom panel starts near its 180px
        height; the user can drag the sash to resize it."""
        try:
            self.root.after(80, self._set_default_bottom_size)
        except tk.TclError:
            pass

    def _set_default_bottom_size(self):
        """Place the editor/bottom split so the bottom panel starts at its
        requested 180px height; the user can drag the sash to resize."""
        try:
            if self.vsplit.winfo_ismapped():
                h = self.vsplit.winfo_height()
                pos = self.vsplit.sashpos(0)
                if h > 0 and pos == 0:
                    self.vsplit.sashpos(0, max(200, h - 230))
        except tk.TclError:
            pass

    def _on_editor_dirty(self, editor, dirty):
        if editor.filepath:
            name = os.path.basename(editor.filepath)
        else:
            name = "Untitled.c"
        if dirty:
            name = "*" + name
        tab = self._tab_for_editor(editor)
        if tab:
            self.notebook.set_label(tab, name)
        if editor is self.current:
            self._update_title()

    def _on_cursor(self, editor, line, col):
        if editor is self.current:
            self._update_status_file()

    def _selected_chars(self, ed):
        try:
            first = ed.content.index("sel.first")
            last = ed.content.index("sel.last")
        except tk.TclError:
            return 0
        if not first or not last or first == last:
            return 0
        try:
            return int(ed.content.count(first, last, "chars")[0])
        except tk.TclError:
            return 0

    def _tab_for_editor(self, editor):
        for holder in self.notebook.tabs():
            frame = self.notebook.nametowidget(holder)
            if getattr(frame, "editor", None) is editor:
                return holder
        return None

    def save_current(self):
        ed = self._current()
        if not ed:
            return
        if not ed.filepath:
            return self.save_as_current()
        try:
            ed.save_file(ed.filepath)
        except OSError as exc:
            dialogs.show_error(self.root, "Save", str(exc))
        self._update_title()
        self._on_editor_dirty(ed, False)

    def save_as_current(self):
        ed = self._current()
        if not ed:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Save Source File",
            defaultextension=".c",
            filetypes=[("C source", "*.c"),
                       ("C++ source", "*.cpp;*.cc;*.cxx"),
                       ("C/C++ source", "*.c;*.cpp;*.cc;*.cxx"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            ed.save_file(path)
        except OSError as exc:
            dialogs.show_error(self.root, "Save", str(exc))
            return
        self.settings.add_recent(path)
        self._update_recent_menu()
        self.explorer.refresh()
        self._update_title()
        self._on_editor_dirty(ed, False)

    def _close_tab_by_tab(self, tab):
        frame = self.notebook.nametowidget(tab)
        ed = getattr(frame, "editor", None)
        if ed:
            self.close_tab(ed)

    def _confirm_unsaved(self, name):
        t = THEMES.get(self.settings.get("theme", "Light"), THEMES["Light"])
        result = []
        dlg = tk.Toplevel(self.root)
        dlg.title("Unsaved Changes")
        dlg.configure(bg=t["window_bg"])
        dlg.transient(self.root)
        dlg.resizable(False, False)
        dlg.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))

        def choose(choice):
            result.append(choice)
            dlg.destroy()

        ttk.Label(
            dlg,
            text='Do you want to save the changes to "%s"?' % name,
            padding=(16, 14, 16, 0)).pack(anchor="w")
        ttk.Label(
            dlg, text="Your changes will be lost if you don't save them.",
            foreground=t["fg_muted"], padding=(16, 2, 16, 10)).pack(anchor="w")
        btns = ttk.Frame(dlg)
        btns.pack(fill="x", pady=(0, 12), padx=16)
        for label, choice in (("Save", "save"),
                              ("Don't Save", "discard"),
                              ("Cancel", "cancel")):
            ttk.Button(btns, text=label, width=12,
                       command=lambda c=choice: choose(c)).pack(
                side="left", padx=(0, 6))
        dlg.update_idletasks()
        x = self.root.winfo_rootx() + \
            (self.root.winfo_width() - dlg.winfo_width()) // 2
        y = self.root.winfo_rooty() + \
            (self.root.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry("+%d+%d" % (x, y))
        dlg.lift()
        dlg.grab_set()
        self.root.wait_window(dlg)
        return result[0] if result else "cancel"

    def close_tab(self, ed):
        if ed.is_dirty():
            ans = self._confirm_unsaved(ed.display_name())
            if ans == "cancel":
                return
            if ans == "save":
                if not ed.filepath:
                    path = filedialog.asksaveasfilename(
                        parent=self.root, title="Save Source File",
                        defaultextension=".c",
                        filetypes=[("C source", "*.c"),
                                   ("C++ source", "*.cpp;*.cc;*.cxx"),
                                   ("C/C++ source", "*.c;*.cpp;*.cc;*.cxx"),
                                   ("All files", "*.*")])
                    if not path:
                        return
                    ed.filepath = path
                try:
                    ed.save_file(ed.filepath)
                except OSError as exc:
                    dialogs.show_error(self.root, "Save", str(exc))
                    return
        tab = self._tab_for_editor(ed)
        if tab:
            self.notebook.forget(tab)
            frame = self.notebook.nametowidget(tab)
            if frame.winfo_exists():
                frame.destroy()
        if self.current is ed:
            self.current = None
        self._update_title()

    def close_current_tab(self):
        ed = self._current()
        if ed:
            self.close_tab(ed)

    def _close_other_tabs(self):
        current = self._current()
        for holder in list(self.notebook.tabs()):
            frame = self.notebook.nametowidget(holder)
            if getattr(frame, "editor", None) is not current:
                self.notebook.forget(holder)

    def _tab_context_menu(self, event):
        self._tab_menu.tk_popup(event.x_root, event.y_root)

    def rename_current(self, newpath):
        ed = self.current
        if ed:
            ed.filepath = newpath
            self._on_editor_dirty(ed, ed.is_dirty())

    def current_path(self):
        ed = self._current()
        return ed.filepath if ed else None

    # ------------------------------------------------------------------
    #  find / replace / goto
    # ------------------------------------------------------------------

    def _invoke_edit(self, op):
        ed = self._current()
        if not ed:
            return
        if op == "undo":
            ed._undo()
        elif op == "redo":
            ed._redo()
        elif op in ("cut", "copy", "paste"):
            try:
                ed.content.event_generate("<<%s>>" % op.title())
            except tk.TclError:
                pass

    def _edit_method(self, name):
        ed = self._current()
        if ed:
            getattr(ed, name)()

    def show_find(self):
        ed = self._current()
        if not ed:
            return
        tab = self._tab_for_editor(ed)
        frame = self.notebook.nametowidget(tab)
        frame.findbar.show_find()
        self.notebook.select(tab)

    def show_replace(self):
        ed = self._current()
        if not ed:
            return
        tab = self._tab_for_editor(ed)
        frame = self.notebook.nametowidget(tab)
        frame.findbar.show_replace()
        self.notebook.select(tab)

    def go_to_line(self):
        ed = self._current()
        if not ed:
            return
        line = dialogs.ask_int(self.root, "Go to Line", "Line number:",
                               minvalue=1, initialvalue=1)
        if line:
            ed.goto_line(line)

    # ------------------------------------------------------------------
    #  project / explorer
    # ------------------------------------------------------------------

    def new_project_dialog(self):
        path = filedialog.askdirectory(
            parent=self.root, title="Choose a folder for the new project")
        if not path:
            return
        name = dialogs.ask_string(self.root, "New Project", "Project name:",
                                  initial=os.path.basename(path))
        if not name:
            return
        if os.listdir(path) and not project_exists(path):
            if not dialogs.ask_yes_no(
                    self.root, "New Project",
                    "Folder is not empty. Continue?"):
                return
        try:
            project = create_project(path, name)
        except OSError as exc:
            dialogs.show_error(self.root, "New Project", str(exc))
            return
        self.set_project(project)
        self.open_file(project.source_files()[0])

    def open_project_dialog(self):
        path = filedialog.askdirectory(parent=self.root,
                                       title="Open C Project")
        if not path:
            return
        try:
            if project_exists(path):
                project = Project.load(path)
            else:
                project = Project(path)
        except Exception as exc:
            dialogs.show_error(self.root, "Open Project", str(exc))
            return
        self.set_project(project)
        sources = project.source_files()
        if sources:
            self.open_file(sources[0])

    def set_project(self, project):
        self.project = project
        self.explorer.set_project(project)
        self._update_title()

    def open_folder_dialog(self):
        path = filedialog.askdirectory(parent=self.root, title="Open Folder")
        if not path:
            return
        self.project = None
        self.explorer.set_root(path)
        self._update_title()

    def rename_editors(self, old_path, new_path):
        """Update every open editor whose file was renamed."""
        old_path = os.path.abspath(old_path)
        new_path = os.path.abspath(new_path)
        for holder in self.notebook.tabs():
            frame = self.notebook.nametowidget(holder)
            ed = getattr(frame, "editor", None)
            if ed and ed.filepath and \
                    os.path.abspath(ed.filepath) == old_path:
                ed.filepath = new_path
                self._on_editor_dirty(ed, ed.is_dirty())
                if ed is self.current:
                    self._update_title()

    def close_editor_for(self, path, was_dir=False):
        """Force-close editor tabs for a deleted file (or a file inside a
        deleted folder) without prompting to save."""
        path = os.path.abspath(path)
        for holder in list(self.notebook.tabs()):
            frame = self.notebook.nametowidget(holder)
            ed = getattr(frame, "editor", None)
            if not ed or not ed.filepath:
                continue
            fp = os.path.abspath(ed.filepath)
            if fp == path or (was_dir and fp.startswith(path + os.sep)):
                self.notebook.forget(holder)
                if frame.winfo_exists():
                    frame.destroy()
                if self.current is ed:
                    self.current = None
        self._update_title()

    # ------------------------------------------------------------------
    #  build / run
    # ------------------------------------------------------------------

    def _context(self):
        """Return (sources, out_exe, build_dir, cwd) or None."""
        if self.project:
            sources = self.project.source_files()
            if not sources:
                return None
            return (sources, self.project.exe_path(),
                    self.project.build_dir(), self.project.directory)
        ed = self._current()
        if not ed or not ed.filepath:
            return None
        src = ed.filepath
        build_dir = os.path.join(USER_DATA_DIR, "build",
                                 os.path.splitext(os.path.basename(src))[0])
        exe = os.path.join(build_dir,
                           os.path.splitext(os.path.basename(src))[0]
                           + ".exe")
        return ([src], exe, build_dir, os.path.dirname(src))

    def _needs_compile(self, exe_path, sources):
        if not os.path.isfile(exe_path):
            return True
        exe_mtime = os.path.getmtime(exe_path)
        # Check source files
        for s in sources:
            if os.path.isfile(s) and \
                    os.path.getmtime(s) > exe_mtime:
                return True
        # Check local header dependencies
        all_headers = self._collect_headers(sources)
        for h in all_headers:
            if os.path.isfile(h) and \
                    os.path.getmtime(h) > exe_mtime:
                return True
        # Invalidate if build settings changed since last build
        if self._build_settings_changed():
            return True
        return False

    def _collect_headers(self, sources):
        """Scan source files for #include "..." of local headers and
        return their absolute paths (recursively)."""
        import re
        include_re = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.MULTILINE)
        visited = set()
        result = []
        queue = list(sources)
        while queue:
            src = queue.pop(0)
            src_dir = os.path.dirname(src)
            try:
                with open(src, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            for m in include_re.finditer(text):
                inc = os.path.normpath(os.path.join(src_dir, m.group(1)))
                if inc not in visited:
                    visited.add(inc)
                    result.append(inc)
                    queue.append(inc)
        return result

    def _build_settings_changed(self):
        """Return True if the compiler path or extra_flags differ from
        what was last used for a build."""
        gcc = self.settings.get("compiler_path", "")
        flags = self.settings.get("extra_flags", "")
        key = (gcc, flags)
        if not hasattr(self, "_last_build_settings"):
            self._last_build_settings = None
        changed = self._last_build_settings is not None and \
                  self._last_build_settings != key
        return changed

    def _record_build_settings(self):
        """Snapshot the current compiler path + extra_flags after a
        successful build so we can detect changes later."""
        self._last_build_settings = (
            self.settings.get("compiler_path", ""),
            self.settings.get("extra_flags", ""),
        )

    def _save_all_dirty(self):
        for holder in self.notebook.tabs():
            frame = self.notebook.nametowidget(holder)
            ed = getattr(frame, "editor", None)
            if ed and ed.is_dirty() and ed.filepath:
                try:
                    ed.save_file(ed.filepath)
                except OSError as exc:
                    dialogs.show_error(self.root, "Save",
                                       "Could not save %s:\n%s"
                                       % (ed.display_name(), exc))

    def compile_current(self, run_after=False):
        if self.build_busy:
            self.status_msg("Build already running")
            return
        ctx = self._context()
        if not ctx:
            self.status_msg("No source file to compile")
            self.terminal.write_line("Nothing to compile - open a source file "
                                     "first.", "err")
            self.compilelog.note_error("Nothing to compile - open a source file "
                                       "first.")
            return
        sources, out_exe, build_dir, cwd = ctx
        if self.settings.get("auto_save_before_build", True):
            self._save_all_dirty()

        try:
            os.makedirs(build_dir, exist_ok=True)
        except OSError as exc:
            self.status_msg("Could not create build directory")
            self.terminal.write_line(
                "Could not create build directory: %s" % exc, "err")
            self.compilelog.note_error(
                "Could not create build directory: %s" % exc)
            return

        self.build_busy = True
        self.status_msg("Compiling...")
        self.tb_compile.configure(state="disabled")
        self.tb_run.configure(state="disabled")
        self.compilelog.begin(sources)

        def on_command(cmd):
            self.compilelog.log_command(cmd)

        def on_finish(result):
            self.build_busy = False
            self.tb_compile.configure(state="normal")
            self.tb_run.configure(state="normal")
            self.problems.set_problems(result.problems)
            nerr = sum(1 for p in result.problems
                       if p.get("severity") == "error")
            nwar = sum(1 for p in result.problems
                       if p.get("severity") == "warning")
            if result.compiler_missing:
                self.compilelog.log_output(result.full_output)
                self.compilelog.end(False, None, result.elapsed)
                self.compilelog.note_error("Compiler not found - configure "
                                           "in View > Settings")
                self.status_msg("Compiler not found - configure in "
                                "View > Settings")
                self.lbl_gcc.configure(text="GCC: not found")
                self.bottom.select(self.compilelog)
                return
            self.compilelog.log_output(result.full_output)
            self.compilelog.end(result.success, result.exit_code,
                                result.elapsed, nerr, nwar)
            if result.success:
                self._record_build_settings()
                self.status_msg("Build successful: %s"
                                % os.path.basename(out_exe))
                self.compilelog.write_line(
                    "Output: %s" % out_exe, "ok")
                if run_after:
                    self._launch(out_exe, cwd)
            else:
                self.status_msg("Build failed - see Compile Log / Problems")
                self.compilelog.note_error("Build failed.")
                self.bottom.select(self.compilelog)

        self.builder.compile(sources, out_exe, build_dir, on_finish,
                             on_command=on_command)

    def run_current(self):
        if self.running:
            self.status_msg("Program already running")
            return
        ctx = self._context()
        if not ctx:
            self.terminal.write_line("Nothing to run - open a source file "
                                     "first.", "err")
            return
        sources, out_exe, build_dir, cwd = ctx
        if self._needs_compile(out_exe, sources):
            self.compile_current(run_after=True)
        else:
            self._launch(out_exe, cwd)

    def _launch(self, exe, cwd):
        self.runner.run(exe, cwd, on_exit=self.on_run_finished)

    def stop_current(self):
        self.runner.stop()

    def set_running_state(self, running):
        self.running = running
        if running:
            self.tb_run.configure(state="disabled")
            self.tb_stop.configure(state="normal")
            self.status_msg("Running...")
        else:
            self.tb_run.configure(state="normal")
            self.tb_stop.configure(state="disabled")

    def on_run_finished(self, code, elapsed):
        self.status_msg("Program finished in %.2fs (exit code %d)"
                        % (elapsed, code))

    # ------------------------------------------------------------------
    #  examples / shortcuts / about
    # ------------------------------------------------------------------

    def show_examples(self):
        t = THEMES.get(self.settings.get("theme", "Light"), THEMES["Light"])
        win = tk.Toplevel(self.root)
        win.title("Built-in Examples")
        win.geometry("420x460")
        win.configure(bg=t["window_bg"])
        win.transient(self.root)

        def themed_listbox(parent, **kw):
            box = tk.Listbox(parent, **kw)
            box.configure(bg=t["input_bg"], fg=t["input_fg"],
                          selectbackground=t["sel_bg"],
                          selectforeground=t["sel_fg"],
                          highlightthickness=1,
                          highlightbackground=t["border"],
                          highlightcolor=t["border"],
                          relief="flat", bd=0)
            return box

        left = ttk.Frame(win)
        left.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(left, text="Console Programs").pack(anchor="w")
        lbox1 = themed_listbox(left, height=10)
        lbox1.pack(fill="both", expand=True, pady=(0, 8))
        ttk.Label(left, text="Computer Graphics").pack(anchor="w")
        lbox2 = themed_listbox(left, height=16)
        lbox2.pack(fill="both", expand=True)

        self._example_paths = []
        for category, title, path in list_examples():
            box = lbox1 if category == "console" else lbox2
            box.insert("end", title)
            self._example_paths.append((category, box, title, path))

        def open_selected(box):
            sel = box.curselection()
            if not sel:
                return
            matches = [p for p in self._example_paths if p[1] is box]
            idx = sel[0]
            if 0 <= idx < len(matches):
                self.open_file(matches[idx][3])
                win.destroy()

        lbox1.bind("<Double-1>", lambda e: open_selected(lbox1))
        lbox2.bind("<Double-1>", lambda e: open_selected(lbox2))

        right = ttk.Frame(win)
        right.pack(side="right", fill="y", padx=6, pady=6)
        ttk.Button(right, text="Open",
                   command=lambda: open_selected(
                       lbox1 if lbox1.curselection() else lbox2)) \
            .pack(fill="x", pady=2)
        ttk.Button(right, text="Close", command=win.destroy) \
            .pack(fill="x", pady=2)

    def show_shortcuts(self):
        lines = ["%s  -  %s" % (k, v) for k, v in MENU_SHORTCUTS]
        dialogs.show_info(self.root, "Keyboard Shortcuts",
                          "\n".join(lines))

    def show_about(self):
        dialogs.show_info(
            self.root, "About",
            "%s %s\n\n"
            "A lightweight C IDE for students with Turbo C / BGI "
            "graphics compatibility.\n\n"
            "Compiler: GNU GCC (MinGW)\n"
            "Graphics: native Windows GDI\n"
            "Works completely offline.\n"
            "%s" % (APP_NAME, APP_VERSION, self.lbl_gcc.cget("text")))

    def check_for_updates(self):
        """Check GitHub Releases for a newer version."""
        import threading
        import urllib.request
        import json
        import os

        # Read GitHub configuration from github_config.ini
        github_owner = "17NitinRaj06"
        github_repo = "C-Lite-IDE"
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "github_config.ini")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GITHUB_OWNER"):
                        github_owner = line.split("=", 1)[1].strip()
                    elif line.startswith("GITHUB_REPO"):
                        github_repo = line.split("=", 1)[1].strip()
        except Exception:
            pass  # Use defaults if config not found

        API_URL = f"https://api.github.com/repos/{github_owner}/{github_repo}/releases/latest"

        def do_check():
            try:
                req = urllib.request.Request(API_URL, headers={"User-Agent": "C-Lite-IDE"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
                
                latest_version = data.get("tag_name", "").lstrip("v")
                release_url = data.get("html_url", "")
                release_notes = data.get("body", "No release notes provided.")
                
                # Compare versions
                current = APP_VERSION
                if self._version_compare(latest_version, current) > 0:
                    # New version available
                    self.root.after(0, lambda: self._show_update_available(latest_version, current, release_url, release_notes))
                else:
                    # Up to date
                    self.root.after(0, lambda: self._show_up_to_date(current))
                    
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    self.root.after(0, lambda: dialogs.show_info(self.root, "Check for Updates",
                        "No releases found on GitHub.\n\n"
                        "Repository: %s/%s\n"
                        "Please check the repository settings." % (github_owner, github_repo)))
                else:
                    self.root.after(0, lambda: dialogs.show_error(self.root, "Check for Updates",
                        "Failed to check for updates (HTTP %d): %s" % (e.code, e.reason)))
            except Exception as e:
                self.root.after(0, lambda: dialogs.show_error(self.root, "Check for Updates",
                    "Failed to check for updates: %s" % str(e)))

        threading.Thread(target=do_check, daemon=True).start()
        dialogs.show_info(self.root, "Check for Updates", "Checking for updates...\n\nThis may take a few seconds.")

    def _version_compare(self, v1, v2):
        """Compare two semantic version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal."""
        def parse(v):
            parts = []
            for p in v.split("."):
                try:
                    parts.append(int(p))
                except ValueError:
                    parts.append(0)
            return parts
        p1 = parse(v1)
        p2 = parse(v2)
        # Pad to same length
        while len(p1) < 3: p1.append(0)
        while len(p2) < 3: p2.append(0)
        for a, b in zip(p1, p2):
            if a > b: return 1
            if a < b: return -1
        return 0

    def _show_update_available(self, latest, current, url, notes):
        """Show dialog when update is available."""
        import webbrowser
        t = THEMES.get(self.settings.get("theme", "Light"), THEMES["Light"])
        dlg = tk.Toplevel(self.root)
        dlg.title("Update Available")
        dlg.configure(bg=t["window_bg"])
        dlg.transient(self.root)
        dlg.resizable(False, False)
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)

        msg = ("A new version of %s is available.\n\n"
               "Current version: %s\n"
               "Latest version: %s\n") % (APP_NAME, current, latest)
        
        ttk.Label(dlg, text=msg, padding=(16, 14, 16, 0)).pack(anchor="w")
        
        # Release notes (truncated)
        notes_short = notes[:500] + ("..." if len(notes) > 500 else "")
        ttk.Label(dlg, text="Release Notes:", padding=(16, 8, 16, 0)).pack(anchor="w")
        notes_frame = ttk.Frame(dlg)
        notes_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        notes_text = tk.Text(notes_frame, height=6, width=60, wrap="word",
                             bg=t["input_bg"], fg=t["input_fg"],
                             relief="flat", bd=0)
        notes_text.insert("1.0", notes_short)
        notes_text.configure(state="disabled")
        notes_text.pack(fill="both", expand=True)
        
        btns = ttk.Frame(dlg)
        btns.pack(fill="x", pady=(0, 12), padx=16)
        
        def open_release():
            webbrowser.open(url)
            dlg.destroy()
        
        def close_dlg():
            dlg.destroy()
        
        ttk.Button(btns, text="View Release", width=14, command=open_release).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Download", width=14, command=lambda: (webbrowser.open(url), dlg.destroy())).pack(side="left", padx=6)
        ttk.Button(btns, text="Later", width=14, command=close_dlg).pack(side="right")
        
        dlg.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dlg.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry("+%d+%d" % (x, y))
        dlg.lift()
        dlg.grab_set()

    def _show_up_to_date(self, current):
        """Show dialog when already up to date."""
        dialogs.show_info(self.root, "Check for Updates",
            "You are using the latest version of %s.\n\nVersion %s" % (APP_NAME, current))

    # ------------------------------------------------------------------
    #  settings / theme
    # ------------------------------------------------------------------

    def set_theme(self, name):
        self.settings.set("theme", name)
        self.apply_theme(name)

    def apply_theme(self, name):
        t = THEMES.get(name, THEMES["Light"])
        dialogs.apply_theme(name)
        self.root.configure(bg=t["window_bg"])
        st = self.style
        try:
            st.configure(".", background=t["window_bg"],
                         foreground=t["panel_fg"])
            st.configure("TFrame", background=t["window_bg"])
            st.configure("TLabel", background=t["window_bg"],
                         foreground=t["panel_fg"])
            st.configure("Muted.TLabel", background=t["window_bg"],
                         foreground=t["fg_muted"])
            st.configure("TButton",
                         background=t["btn_bg"], foreground=t["btn_fg"],
                         bordercolor=t["border"], borderwidth=1,
                         relief="flat", padding=(8, 3), focusthickness=0)
            st.map("TButton",
                   background=[("active", t["btn_hover"]),
                               ("pressed", t["btn_press"])],
                   bordercolor=[("active", t["border"])],
                   foreground=[("disabled", t["fg_disabled"])])
            st.configure("TEntry", fieldbackground=t["input_bg"],
                         foreground=t["input_fg"],
                         insertcolor=t["input_fg"],
                         bordercolor=t["border"], padding=(6, 2))
            st.map("TEntry",
                   bordercolor=[("focus", t["accent"])],
                   foreground=[("disabled", t["fg_disabled"])],
                   fieldbackground=[("disabled", t["btn_bg"])])
            st.configure("TSpinbox", fieldbackground=t["input_bg"],
                         foreground=t["input_fg"],
                         arrowcolor=t["panel_fg"],
                         bordercolor=t["border"], padding=(6, 2))
            st.configure("TCombobox", fieldbackground=t["input_bg"],
                         background=t["input_bg"],
                         foreground=t["input_fg"],
                         arrowcolor=t["panel_fg"],
                         bordercolor=t["border"], padding=(6, 2))
            st.map("TCombobox",
                   fieldbackground=[("readonly", t["input_bg"])],
                   bordercolor=[("focus", t["accent"])])
            st.configure("TCheckbutton", background=t["window_bg"],
                         foreground=t["panel_fg"])
            st.configure("TNotebook", background=t["window_bg"],
                         borderwidth=0)
            st.configure("TNotebook.Tab",
                         background=t["tab_bg"], foreground=t["tab_fg"],
                         borderwidth=0, padding=(8, 5))
            st.map("TNotebook.Tab",
                   background=[("selected", t["tab_active_bg"]),
                               ("active", t["tab_hover_bg"])],
                   foreground=[("selected", t["tab_active_fg"])])
            st.configure("Treeview",
                         background=t["bottom_bg"],
                         fieldbackground=t["bottom_bg"],
                         foreground=t["editor_fg"],
                         bordercolor=t["border"], borderwidth=1,
                         rowheight=22)
            st.map("Treeview",
                   background=[("selected", t["sel_bg"])],
                   foreground=[("selected", t["sel_fg"])])
            st.configure("Explorer.Treeview",
                         background=t["sidebar_bg"],
                         fieldbackground=t["sidebar_bg"],
                         foreground=t["panel_fg"],
                         bordercolor=t["border"], borderwidth=1,
                         rowheight=22)
            st.map("Explorer.Treeview",
                   background=[("selected", t["sel_bg"])],
                   foreground=[("selected", t["sel_fg"])])
            st.configure("Treeview.Heading",
                         background=t["panel_bg"],
                         foreground=t["panel_fg"],
                         bordercolor=t["border"], relief="flat",
                         padding=(4, 2))
            st.map("Treeview.Heading",
                   background=[("active", t["btn_hover"])])
            st.configure("Vertical.TScrollbar",
                         background=t["sb_bg"],
                         troughcolor=t["sb_trough"],
                         bordercolor=t["sb_trough"], arrowsize=0,
                         relief="flat", width=12)
            st.map("Vertical.TScrollbar",
                   background=[("active", t["sb_hover"])])
            st.configure("Horizontal.TScrollbar",
                         background=t["sb_bg"],
                         troughcolor=t["sb_trough"],
                         bordercolor=t["sb_trough"], arrowsize=0,
                         relief="flat", width=12)
            st.map("Horizontal.TScrollbar",
                   background=[("active", t["sb_hover"])])
            st.configure("TSeparator", background=t["border"])
        except tk.TclError:
            pass
        for option, value in (
                ("*Listbox.background", t["input_bg"]),
                ("*Listbox.foreground", t["input_fg"]),
                ("*Listbox.selectBackground", t["sel_bg"]),
                ("*Listbox.selectForeground", t["sel_fg"])):
            self.root.option_add(option, value)
        for menu in self._menus:
            style_menu(menu, t)
        for holder in self.notebook.tabs():
            frame = self.notebook.nametowidget(holder)
            ed = getattr(frame, "editor", None)
            if ed:
                ed.apply_theme(name)
        self.terminal.apply_theme(name)
        self.problems.apply_theme(name)
        self.compilelog.apply_theme(name)
        self.explorer.apply_theme(name)
        self.lbl_theme.configure(text=name)

    def show_settings(self):
        t = THEMES.get(self.settings.get("theme", "Light"), THEMES["Light"])
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.configure(bg=t["window_bg"])
        win.transient(self.root)
        win.resizable(False, False)
        pad = {"padx": 8, "pady": 4}
        row = 0

        gcc, source = compiler_source(
            self.settings.get("compiler_path", ""))
        if gcc:
            ver = gcc_version(gcc) or os.path.basename(gcc)
            src_label = {"bundled": "Bundled MinGW GCC — Detected",
                         "custom": "Custom GCC — Detected",
                         "path": "System GCC (PATH) — Detected",
                         "auto": "GCC — Detected"}.get(source, "GCC")
        else:
            ver = None
            src_label = "GCC not found"
        ttk.Label(win, text="Compiler:", padding=(8, 10, 8, 2)).grid(
            row=row, column=0, sticky="w", **pad)
        ttk.Label(win, text=src_label,
                  foreground=(t["status_ok"] if gcc else t["status_err"])).grid(
            row=row, column=1, sticky="w", **pad)
        row += 1
        ttk.Label(win, text="Version:", padding=(8, 2, 8, 2)).grid(
            row=row, column=0, sticky="w", **pad)
        ttk.Label(win, text=ver or "—").grid(row=row, column=1,
                                             sticky="w", **pad)
        row += 1
        ttk.Separator(win, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="we",
            padx=8, pady=6)
        row += 1

        ttk.Label(win, text="Theme:").grid(row=row, column=0, sticky="w",
                                           **pad)
        theme_var = tk.StringVar(value=self.settings.get("theme"))
        ttk.Combobox(win, textvariable=theme_var, values=list(THEMES),
                     state="readonly", width=24).grid(row=row, column=1,
                                                      **pad)
        row += 1

        ttk.Label(win, text="Font family:").grid(row=row, column=0,
                                                 sticky="w", **pad)
        font_var = tk.StringVar(value=self.settings.get("font_family"))
        ttk.Combobox(win, textvariable=font_var,
                     values=["Consolas", "Courier New", "Lucida Console",
                             "Cascadia Mono", "Monaco", "DejaVu Sans Mono"],
                     width=24).grid(row=row, column=1, **pad)
        row += 1

        ttk.Label(win, text="Font size:").grid(row=row, column=0,
                                               sticky="w", **pad)
        size_var = tk.IntVar(value=int(self.settings.get("font_size")))
        ttk.Spinbox(win, from_=8, to=24, textvariable=size_var, width=24) \
            .grid(row=row, column=1, **pad)
        row += 1

        ttk.Label(win, text="Tab size:").grid(row=row, column=0,
                                              sticky="w", **pad)
        tab_var = tk.IntVar(value=int(self.settings.get("tab_size")))
        ttk.Spinbox(win, from_=1, to=8, textvariable=tab_var, width=24) \
            .grid(row=row, column=1, **pad)
        row += 1

        use_tabs_var = tk.BooleanVar(value=self.settings.get("use_tabs"))
        ttk.Checkbutton(win, text="Insert tabs instead of spaces",
                        variable=use_tabs_var).grid(row=row, column=0,
                                                    columnspan=2, **pad)
        row += 1

        ttk.Label(win, text="GCC path:").grid(row=row, column=0,
                                              sticky="w", **pad)
        gcc_var = tk.StringVar(value=self.settings.get("compiler_path"))
        entry = ttk.Entry(win, textvariable=gcc_var, width=18)
        entry.grid(row=row, column=1, sticky="we", **pad)

        def browse_gcc():
            p = filedialog.askopenfilename(
                parent=win, title="Select gcc.exe",
                filetypes=[("gcc", "gcc.exe"), ("All files", "*.*")])
            if p:
                gcc_var.set(p)
        ttk.Button(win, text="...", width=3, command=browse_gcc) \
            .grid(row=row, column=2, padx=(0, 8))
        row += 1

        ttk.Label(win, text="Extra flags:").grid(row=row, column=0,
                                                 sticky="w", **pad)
        flags_var = tk.StringVar(value=self.settings.get("extra_flags"))
        ttk.Entry(win, textvariable=flags_var, width=24).grid(
            row=row, column=1, **pad)
        row += 1

        auto_var = tk.BooleanVar(
            value=self.settings.get("auto_save_before_build"))
        ttk.Checkbutton(win, text="Auto-save before building",
                        variable=auto_var).grid(row=row, column=0,
                                                columnspan=2, **pad)
        row += 1

        def apply():
            self.settings.set("theme", theme_var.get())
            self.settings.set("font_family", font_var.get())
            self.settings.set("font_size", int(size_var.get()))
            self.settings.set("tab_size", int(tab_var.get()))
            self.settings.set("use_tabs", bool(use_tabs_var.get()))
            self.settings.set("compiler_path", gcc_var.get().strip())
            self.settings.set("extra_flags", flags_var.get().strip())
            self.settings.set("auto_save_before_build",
                              bool(auto_var.get()))
            for holder in self.notebook.tabs():
                frame = self.notebook.nametowidget(holder)
                ed = getattr(frame, "editor", None)
                if ed:
                    ed.update_font()
            self.apply_theme(theme_var.get())
            self._update_compiler_status()
            win.destroy()

        ttk.Button(win, text="Apply", command=apply).grid(
            row=row, column=0, pady=10)
        ttk.Button(win, text="Cancel", command=win.destroy).grid(
            row=row, column=1, pady=10)

    # ------------------------------------------------------------------
    #  status
    # ------------------------------------------------------------------

    def status_msg(self, msg):
        self.status.configure(cursor="")
        self.status_var = msg
        self.lbl_file.configure(text=msg + ("   |   " if self.current
                                            and self.current.filepath
                                            else ""))

    def _update_title(self):
        if self.project:
            title = "%s %s - [%s]" % (APP_NAME, APP_VERSION,
                                      self.project.name)
        else:
            ed = self._current()
            if ed:
                title = "%s %s - [%s]" % (APP_NAME, APP_VERSION,
                                          ed.display_name())
            else:
                title = "%s %s" % (APP_NAME, APP_VERSION)
        self.root.title(title)
        self._update_status_file()

    def _update_status_file(self):
        ed = self._current()
        if ed:
            label = "%s%s" % ("*" if ed.is_dirty() else "",
                              ed.filepath or ed.display_name())
            self.lbl_file.configure(text=label)
            line = int(ed.content.index("insert").split(".")[0])
            col = int(ed.content.index("insert").split(".")[1])
            self.lbl_pos.configure(text="Ln %d, Col %d" % (line, col))
            self.lbl_sel.configure(text="Sel: %d" % self._selected_chars(ed))
            self.lbl_lines.configure(text="Lines: %d" % ed.get_line_count())
        else:
            self.lbl_file.configure(text="")
            self.lbl_pos.configure(text="")
            self.lbl_sel.configure(text="Sel: 0")
            self.lbl_lines.configure(text="")

    def _update_compiler_status(self):
        gcc, source = compiler_source(
            self.settings.get("compiler_path", ""))
        if not gcc:
            self.lbl_gcc.configure(text="GCC: not found")
        else:
            ver = gcc_version(gcc) or os.path.basename(gcc)
            self.lbl_gcc.configure(text="GCC: " + ver)

    def _update_recent_menu(self):
        self.recent_menu.delete(0, "end")
        for p in self.settings.get("recent_files", [])[:10]:
            self.recent_menu.add_command(
                label=p,
                command=lambda p=p: self.open_file(p))

    def navigate(self, path, line):
        ed = self.open_file(path)
        if ed:
            ed.goto_line(line)

    # ------------------------------------------------------------------

    def on_close(self):
        for holder in list(self.notebook.tabs()):
            frame = self.notebook.nametowidget(holder)
            ed = getattr(frame, "editor", None)
            if ed and ed.is_dirty():
                ans = dialogs.ask_yes_no_cancel(
                    self.root, "Exit",
                    "Save changes to %s?" % ed.display_name())
                if ans is None:
                    return False
                if ans and not ed.filepath:
                    path = filedialog.asksaveasfilename(
                        parent=self.root, title="Save Source File",
                        defaultextension=".c",
                        filetypes=[("C source", "*.c"),
                                   ("C++ source", "*.cpp;*.cc;*.cxx"),
                                   ("C/C++ source", "*.c;*.cpp;*.cc;*.cxx"),
                                   ("All files", "*.*")])
                    if not path:
                        return False
                    ed.filepath = path
                if ans:
                    try:
                        ed.save_file(ed.filepath)
                    except OSError:
                        return False
        self.runner.stop()
        self.settings.save()
        return True


def main():
    enable_dpi_awareness()
    set_app_user_model_id()
    root = tk.Tk()
    try:
        root.iconbitmap(icon_path())
    except Exception:
        pass
    app = App(root, startup_files=sys.argv[1:])
    root.protocol("WM_DELETE_WINDOW", lambda: (
        root.destroy() if app.on_close() else None))
    root.mainloop()


if __name__ == "__main__":
    main()