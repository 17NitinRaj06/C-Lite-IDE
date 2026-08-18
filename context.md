# C-Lite IDE — Project Context

## Overview
C-Lite IDE is a Windows desktop IDE for C/C++ students, built in Python 3 + Tkinter. It emulates the Turbo C / Borland-era workflow: console programs with `conio.h` (`getch()`, `clrscr()`, etc.) and the `graphics.h`/`graphics.lib` APIs (line, circle, etc.), rendered through a custom Win32 GDI runtime that re-implements the old BGI functions. It is designed to work fully offline using MinGW GCC.

## Environment
- OS: Windows x64
- Python: 3.13.7 (tkinter 8.6)
- Compiler: bundled **MinGW.org GCC 6.3.0 32-bit** at `compiler\mingw\bin\gcc.exe` (no separate GCC install needed). The system `C:\MinGW` copy is no longer a prerequisite.
- Launch: `python clite.py` or `start.bat`; packaged build via `packaging\build_ide.bat` (needs `pyinstaller`, installed).
- No git repository; no package dependencies beyond the Python standard library (+ PyInstaller for the packaged exe).

## Layout
- `clite.py` — entry point.
- `clite_ide/` — application package.
  - `app.py` — main window, editor tabs, menu, toolchain glue.
  - `builder.py` — invokes GCC; `_warm_exe()` triggers Windows Defender first-run scan at build time.
  - `runner.py` — launches the compiled exe on a background thread with a stop guard.
  - `tabs.py` — `ClosableNotebook`: file tabs with an X close button (glyph embedded in the label).
  - (other modules: editor, terminal, explorer, etc.)
- `compiler/mingw/` — bundled 32-bit MinGW toolchain (`bin/`, `include/`, `lib/`, `libexec/`, `share/`; ~218 MB, trimmed from the 386 MB mingw-get install: the `msys/` and `var/` cache dirs are not needed at runtime). Includes gcc.exe, g++.exe, ar.exe, ld.exe, as.exe, and all runtime DLLs (libgcc_s_dw2-1.dll, libstdc++-6.dll, libgmp-10.dll, ...).
- `runtime/bgilite.c` — Win32 GDI re-implementation of BGI `graphics.h`; main thread pumps messages while the gfx window thread spins up.
- `include/` — bundled headers (`conio.h`, `graphics.h`, `dos.h`). Note: no prebuilt `graphics.lib`/`libbgi.a` — the BGI functions are compiled from `runtime/bgilite.c` and linked with `-lgdi32 -lm`.
- `examples/` — `console/` and `graphics/` sample programs.
- `build/` — test scripts: `smoke.py`, `e2e.py`, `input_test.py`, `test_tabs.py`, `test_close_state.py`, `test_dialog_center.py`.
- `clite_ide/dpi.py` — Windows DPI-awareness bootstrap (`enable_dpi_awareness()`).
- `clite_ide/windows.py` — Windows shell integration (`set_app_user_model_id()`, `icon_path()`/`png_path()`).
- `icons/` — `app.ico` (multi-res feather, 16-256 px) + `app.png` (256 px).
- `packaging/` — build pipeline: `make_icon.py` (regenerates the icons from `tk86t.dll`), `app.rc` (icon + version resource), `build_ide.bat` (windres + PyInstaller → `dist\C-Lite IDE\C-Lite IDE.exe`).
- `settings.json` — user settings; `start.bat` — quick launcher.

## Bundled Compiler (COMPLETE)
The IDE ships with a 32-bit MinGW toolchain (the exact MinGW.org GCC 6.3.0 build the BGI runtime was developed against), so a fresh Windows 10/11 box with only Python 3 works: open a `.c`, click Compile/Run.

- Detection priority in `settings.find_gcc()` / `compiler_source()`:
  1. bundled `compiler\mingw\bin\gcc.exe`
  2. user-configured `compiler_path` from View > Settings
  3. `gcc` on PATH (`shutil.which`)
  4. other common install locations (`C:\MinGW`, `C:\mingw64`, TDM-GCC, MSYS2)
  Falls back gracefully if the bundle is missing/corrupt.
- `builder.py` auto-derives toolchain paths from the detected gcc (`toolchain_root/toolchain_include/toolchain_lib_dir`): adds `-I <toolchain>\include` and `-L <toolchain>\lib`. `Builder.runtime_env()` prepends `<toolchain>\bin` to PATH — required because `libexec\gcc\mingw32\6.3.0\cc1.exe` (and compiled exes) load their DLLs from `bin`. Used by `compile`, `ensure_runtime_objects`, `_warm_exe`, and `Runner.run`.
- `builder._driver_path()` selects `g++.exe` for `.cpp/.cc/.cxx` sources (C++ confirmed working).
- View > Settings shows a status block: `Compiler: Bundled MinGW GCC — Detected` + the detected version; the GCC path option stays for advanced users.
- Verified with `C:\MinGW` stripped from PATH: console compile+run (hello_world), graphics compile (dda_line, circle), C++ compile+run, and `getch`/input/exit-0 flow all pass.

## Key Fix: "hang / getch / exit0" bug (RESOLVED)
The child process appeared to hang before `main()`, drop early terminal input, and leave zombie exes. Root cause was **Windows Defender real-time protection**: the first execution of a freshly compiled exe blocked `CreateProcess`/Popen for 11–17 s (AV first-run scan). Once scanned, launches were instant.

Fixes (all verified):
- `builder._warm_exe()` spawns the fresh exe with `CREATE_SUSPENDED | CREATE_NO_WINDOW` then terminates it, synchronously on the build thread — the AV scan happens during the "Compiling..." step.
- `runner.run()` launches via a background thread so a slow Popen never freezes the Tk UI (`_stop_requested` guard).
- `runtime/bgilite.c` pumps messages while waiting for the gfx window thread; `clite_gfx_thread` calls `PeekMessageA`.

## Current Feature: Tab Close (X) Button (COMPLETE)
- `ClosableNotebook` in `clite_ide/tabs.py`.
- The close glyph `\u2715` is embedded in each tab label: always visible on the active tab, shown on inactive tabs only while hovering over them.
- Clicking the glyph closes only that tab and returns `"break"` (does not select the tab first).
- Dirty tabs show `*name   ✕`; closing a dirty tab opens a custom modal with **Save / Don't Save / Cancel** (`messagebox` can't label the buttons that way).
- `ttk.Notebook.bbox()` returns `(0,0,0,0)` in every theme on this machine, so tab geometry is computed manually from the measured label font (`tkfont`) plus the style padding (`_tab_regions`, `_x_region`). Multi-row wrap is handled.

## Key Fix: file-close state sync (COMPLETE)
Closing a file/tab now fully clears the active-file state: the title drops the `- [name]` (back to `C-Lite IDE 1.0.0`), `lbl_file`/`lbl_pos` in the status bar are emptied, `self.current` is reset, and the closed editor frame is destroyed (content freed). If other tabs remain, the title/path bar switch to the notebook's newly active tab. `_update_title()` handles the no-file case; `_update_status_file()` is the extracted path-bar refresh.

## Key Fix: Unsaved-changes dialog centering (COMPLETE)
`_confirm_unsaved()` now positions the modal exactly at the center of the IDE window: after packing, `update_idletasks()` + `geometry("+x+y")` computed from `root.winfo_rootx/rooty/width/height` (client-area center), so it follows the IDE wherever it sits on screen and stays centered even after the window is moved/resized. `transient(self.root)` + `lift()` keep it above the IDE. Design/title/buttons/behavior unchanged.

## Key Fix: Blurry file dialog / DPI awareness (COMPLETE)
The Open/Save native file picker (and the whole app at >100% scaling) looked blurry because the process was **DPI-unaware**: Windows rendered it at 96 DPI and bitmap-stretched it to the real display scale (this machine's monitor is 120 DPI / 125%). `clite_ide/dpi.py` adds `enable_dpi_awareness()`, which calls `shcore.SetProcessDpiAwareness(SYSTEM_DPI_AWARE)` (falling back to `user32.SetProcessDPIAware()`); it is invoked at the very top of `clite.py` and again in `app.main()` **before** `tk.Tk()`. Verified: process awareness 0→1, Tk `scaling` 1.668 (=120/72), and the native file dialog window reports `GetDpiForWindow == 120` (rendered natively, not stretched). At 100% it's a no-op; the dark Windows file picker, layout, and all functionality are unchanged.

## Current Feature: live status bar + Compile Log (COMPLETE)
The bottom status bar now shows, live: the file path (with `*` when dirty), `Ln x, Col y`, `Sel: <char count>`, `Lines: <n>`, the GCC version, and the theme name. Everything refreshes instantly on cursor move, selection change, edit (key release), tab switch, and open/close:
- The editor already notified the app on `<<Selection>>`/key/button release via `_notify()` → `on_cursor`; `app._on_cursor()` now calls the unified `_update_status_file()` (was `lbl_pos`-only), which also computes `Sel` via `content.count("sel.first","sel.last","chars")` (TclError-guarded, `Sel: 0` when nothing selected) and `Lines` via `ed.get_line_count()`.
- Tab switches were stale before (clicking another tab left `self.current`/title/status on the old file). `app` now binds its own `<<NotebookTabChanged>>` → `_on_notebook_tab_changed()` sets `self.current` to the newly selected tab's editor and calls `_update_title()`. Multiple handlers on the virtual event are fine (ClosableNotebook already binds it internally).
- Closing the last tab clears all four fields (title, path, `Sel: 0`, empty `Lines`); closing one of several switches title/status to the remaining tab. `lbl_file`/`lbl_pos` attribute names are preserved (test_close_state depends on them).

A dedicated **Compile Log** tab now sits between Problems and Terminal (`clite_ide/compilelog.py`, modeled on `terminal.py`: disabled `tk.Text` + bar with Clear button, tags `header/cmd/dim/ok/err/warn`, theme-aware). When Compile/Run is executed it logs `=== Compilation started ===`, the source file(s), the exact compiler command (args with spaces are quoted), the raw GCC output, the exit code, elapsed time, and a `successful`/`FAILED (n errors)` summary. It auto-switches to the Compile Log on failure; on success it stays where you are. Problems still parses errors/warnings for click-to-navigate; Terminal remains purely program I/O (build status messages were moved out of it).

Builder support: `BuildResult` gained `command` (full gcc command list), `exit_code`, and `elapsed`; `Builder.compile()` now also accepts `on_command` (called via `root.after` once the command is built, same worker thread as the existing `on_finish`).

The bottom panel is now resizable: the editor notebook and the bottom notebook sit in a vertical `ttk.Panedwindow` (`self.vsplit`, weight 3:1) instead of `pack(side="bottom", height=180)`. A `<<Map>>` binding on `self.vsplit` defers setting the default sash to `height - 230` until the split is really on screen (setting it earlier — e.g. `after_idle` during `update_idletasks()` — collapsed the editor pane to 1px because the widget isn't mapped yet). The sash is user-draggable after that.

## Current Feature: Project / File Explorer (COMPLETE)
The left sidebar (`clite_ide/explorer.py`, rewritten) is now a real project explorer. It displays the currently opened folder (or project directory) as a **lazy-loaded** `ttk.Treeview` (`show="tree"`, scrollbar), so folders only list their children once expanded:
- Folders are **bold** + get a disclosure arrow (a placeholder child forces the arrow before first open); C/C++ files (`.c .cpp .cc .cxx .c++ .h .hpp`) use the editor foreground tag `cfile`; other files render dimmer (`file`); the `build/` dir is skipped (existing behavior, keeps auto-sync from churning on every compile).
- **Active-file highlight**: the currently open editor file gets an `active` tag (accent/`status_run` color). `open_file` and `_on_notebook_tab_changed` call `explorer.set_active_file(path)`; `_reveal()` lazily expands ancestor folders so a newly opened file is always revealed and scrolled into view.
- **Double-click** a file → `app.open_file` (already dedups: re-clicking an open file just selects its tab, no duplicate). Double-click/Return on a folder toggles expand/collapse.
- **Context menu** (right-click, rebuilt per selection): folders get Open/Expand, New File, New Folder, Rename, Delete; files get Open, Rename, Delete; always Refresh Explorer + Reveal in Explorer. Right-clicking empty space offers New File / New Folder / Refresh.
- **File ops**: New File (any name, opened in a tab after creation), New Folder, Rename (also updates every open editor via `app.rename_editors` and re-highlights), Delete (confirm + `shutil.rmtree`/`os.remove`, force-closes affected editor tabs via `app.close_editor_for`, clears the active highlight if needed).
- **Empty states**: no root → a dim "No folder opened" node; an empty project folder → "(empty folder)" child under the root node.
- **Filesystem sync**: `refresh()` snapshots the tree (os.walk, build/ skipped); a 2 s `root.after` poll (`_auto_sync`) rebuilds only when the snapshot changed, so external create/rename/move/delete shows up. `refresh()` preserves currently-expanded folders and the active highlight across rebuilds.
- **Open Folder**: new **File → Open Folder...** menu item → `app.open_folder_dialog()` → `explorer.set_root(path)` (sets `self.project = None`, switching to folder mode; build falls back to single-file mode, unchanged). `set_project` still maps to `explorer.set_root(project.directory)`. The left pane was already resizable via the `main_pane` `ttk.Panedwindow`.
- `explorer.apply_theme(name)` colors the folder/cfile/file/active/dim tags from the current theme (wired into `app.apply_theme`); fonts are `tkfont` copies (bold folders, italic dim).

## Current Feature: Dark theme redesign (COMPLETE)
The whole UI is now an intentional, cohesive, compact charcoal design system (visual-only; compiler, editor, terminal, explorer, tabs, build/run, and every test unchanged). The **Dark** palette in `clite_ide/settings.py` uses the user-specified charcoal scheme:
- Chrome: app `#181a1f`, sidebar/panels `#17191d`, bottom panels/terminal/compile log `#191b20`, editor `#1e2025`, inputs `#22252b`, borders/dividers `#2e333c`; primary text is a soft light gray `#c5cbd3` with a muted `#8a919e` secondary; accent is a restrained blue `#4e8cc9` (no pure black, no neon).
- Syntax (muted, non-neon): keywords soft lavender `#a48bd1`, types `#6fc2d9`, strings/chars muted orange `#c89a74`, numbers soft cyan `#7bc3c0`, comments muted green-gray `#67796c`, preproc muted magenta `#c08ac0`, functions light blue `#5e9bd6`, constants muted amber `#d6b264`.
- `THEMES` gained new keys in **both** Light and Dark so theme switching can't `KeyError`: `fg_muted`, `border`, `input_bg/fg`, `btn_bg/hover/press/fg`, `fg_disabled`, `tab_bg/hover_bg/active_bg/fg/active_fg`, `sel_bg/sel_fg`, `sb_bg/hover/trough`, `sidebar_bg`, `bottom_bg`, `icon_folder/icon_file`, `menu_bg/fg/hover/hover_fg/disabled`.
- `app.apply_theme()` now configures the full ttk style set (`TButton` flat + hover/pressed maps, `TEntry`/`TSpinbox`/`TCombobox` with focus border, `TNotebook.Tab` compact padding `(8,5)` ~30px tabs, `Treeview` + `Explorer.Treeview` variants, `Treeview.Heading`, dark arrowless `Vertical/Horizontal.TScrollbar`, `TSeparator`); sets `*Listbox.*` option-db colors so the Combobox popdown and any listboxes render dark; re-styles every `tk.Menu` via `uistyle.style_menu()`; `dialogs.apply_theme()` keeps the themed dialogs in sync. The status bar uses a `Muted.TLabel` style for secondary fields, and thin `TSeparator`s frame the toolbar and status bar.
- `clite_ide/dialogs.py` (new): themed replacements for native `simpledialog`/`messagebox` — `ask_string`, `ask_int`, `ask_yes_no`, `ask_yes_no_cancel`, `show_warning/show_error/show_info` — centered over the parent, dark Toplevel + ttk widgets. Used by `app.py` (Go to Line, New Project prompts, save/open errors, Exit confirm, Shortcuts/About) and `explorer.py` (New File/Folder, Rename, Delete confirm, errors). `test_explorer` monkeypatches `exmod.dialogs.ask_string`/`ask_yes_no` now.
- `clite_ide/uistyle.py` (new): `style_menu(menu, t)` shared menu coloring (menubar, dropdowns, tab menu, explorer context menus).
- Explorer: compact `rowheight=22`, `style="Explorer.Treeview"` (sidebar-colored `sidebar_bg`), subtle 12×12 in-memory `PhotoImage` folder/file icons regenerated per theme (`_make_icon`), context menus styled.
- Find/Replace bar is compact (tighter paddings); the examples dialog's listboxes are dark-themed.

## Current Feature: Official app icon + Windows shell integration (COMPLETE)
The app now has a single official icon everywhere — the **Tk quill feather** (the brown feather Tk has always shown in the title bar). New `icons/` assets + packaging:
- `icons/app.ico` — multi-resolution .ico (16/24/32/48/64 px BMP entries + 128/256 px PNG entries, 32-bit alpha). Built by `packaging/make_icon.py`, which **extracts the real feather icon resources from `tk86t.dll`** (RT_GROUP_ICON 1 + RT_ICON 1-13, sizes 16-64 at 32/24/8 bpp), keeps the 32-bit BMP images, and bilinearly upscales the 64 px source to 128/256. `icons/app.png` is the 256 px PNG companion.
- `clite_ide/windows.py` (new): `set_app_user_model_id("C-LiteIDE.App")` calls `shell32.SetCurrentProcessExplicitAppUserModelID` (verified: process AppUserModelID reads back `C-LiteIDE.App`, hr S_OK) so the taskbar keeps the IDE's identity/icon; `icon_path()`/`png_path()` resolve the icon from the project root or the frozen bundle. All safe no-ops on non-Windows / missing file.
- Runtime wiring: `clite.py` calls `set_app_user_model_id()` right after `enable_dpi_awareness()`; `app.main()` also calls it and sets `root.iconbitmap(icon_path())` (TclError-guarded). Verified by capturing the live window icon via `GetClassLongPtr(GCLP_HICON)`+`GetDIBits`: title-bar icon is the feather at 40×40 (32 px × 125% DPI) for **both** `python clite.py` and the packaged exe.
- Packaging (`packaging/build_ide.bat`): (1) compiles `packaging/app.rc` (icon + VS_VERSION_INFO) with the bundled `windres` into `build\app.res` — needs `--preprocessor="gcc -E -xc -DRC_INVOKED"`, toolchain on PATH, and **forward-slash** input/icon paths (this binutils build mangles `\` in gcc `-E` line markers and eats `\a`-style escapes in the .rc); (2) PyInstaller `--onedir --windowed --icon icons\app.ico --add-data "icons;icons" --name "C-Lite IDE"`; (3) copies `compiler/`, `include/`, `runtime/`, `examples/`, `icons/` next to the exe so the bundle is self-contained/offline. Output: `dist\C-Lite IDE\C-Lite IDE.exe`. Requires `pip install pyinstaller` (6.22.2 installed).
- Embedded icon verified with `pefile`: the exe carries RT_GROUP_ICON with all 7 sizes (16/24/32/48/64/128/256) + RT_MANIFEST; `ExtractIconExW` returns both large (32) and small (16) feather icons that render correctly.
- Frozen-aware root: `clite_ide/__init__.py` sets `ROOT` to `dirname(sys.executable)` when `sys.frozen` (packaged), else the project root — so the packaged exe finds the bundled compiler/include/runtime/examples/compiler next to itself. No editor/explorer/tabs/compiler/terminal/run-stop/dark-theme behavior changed.

## Testing
Run from the project root (console encoding is cp1252; set `PYTHONIOENCODING=utf-8` because the ✕ glyph can't print otherwise):
- `build/test_tabs.py` — 18/18 PASS: open/close tabs, active-vs-hover X, leave hides X, X closes the right tab, label click selects, dirty close via Save / Don't Save / Cancel (recursive button finder; keep click coordinates measured *after* hovering, since the label widens when the X appears).
- `build/test_close_state.py` — 17/17 PASS: closing the last tab clears title, `lbl_file`, `lbl_pos`, `app.current`, and the editor frame; the closed name stays gone through `_update_title()`/`status_msg()`/`_current()`; closing one tab among several switches title/path bar to the new active tab.
- `build/test_dialog_center.py` — 3/3 PASS: opens the Unsaved Changes modal (via a dirty close) with the IDE moved off-origin and asserts `geometry("+x+y")` equals the IDE client-area center; Cancel keeps the tab; clean close afterwards.
- `build/test_statusbar.py` — 20/20 PASS: Ln/Col/Sel/Lines live updates on cursor move, selection, and edit; tab switch refreshes current/title/status; close keeps status on the remaining tab; Compile Log tab is ordered Problems→Compile Log→Terminal; a failing compile writes the command + raw output + FAILED and auto-selects the Compile Log; a passing compile writes the success summary; Problems still parses the errors. Note: poll for `build_busy` with `root.after` steps inside `mainloop` — a busy `update()`+`sleep` loop breaks Tk's cross-thread `root.after` marshaling (`RuntimeError: main thread is not in main loop`) which the builder relies on.
- `build/test_explorer.py` — 30/30 PASS: "No folder opened" startup state; root folder node; lazy placeholder-then-load on expand; cfile/file/folder tags (build/ skipped); nested empty folder and empty-root "(empty folder)" message; double-click opens a file tab and reuses the tab when re-clicked; double-click collapses folders; active-file highlight follows open_file and tab switches; New File (creates+opens), New Folder, Rename (updates open editors + re-highlights), Delete (removes file/folder and closes its editor tabs); auto-sync picks up external create/delete; `set_root` switches trees. Note: compare paths with `os.path.normpath(os.path.join(...))` — `os.path.join` on a rel arg containing `/` keeps the forward slash, which won't equal the normalized keys the explorer stores; reselect the tree item after `refresh()` (iids are recreated).
- `build/smoke.py` — app startup/closing.
- `build/e2e.py` — compile + run console example (terminal shows output), compile graphics example.
- `build/input_test.py` — compile, show both scanf prompts, send `getch()`, verify clean exit (exit code 0).

## Notes / Gotchas
- The Windows console (cp1252) cannot print the ✕ glyph — only affects debug prints, not the app.
- All tab selection checks must use `self.select()` (widget path), never `index("current")` (int) — an int-vs-string comparison silently fails.
- `_set_hovered` must clear `_hovered` before re-rendering the old tab, or the X is re-added (`_shows_close` consults `_hovered`).
- `TNotebook.Tab` left/right padding is load-bearing for `test_tabs`: it clicks the X at `bx + bw - 8` (via `_x_region`, which subtracts the style's right padding), so keep padding ≈ `(8, 5, 8, 5)` (height ~30px, right edge math intact).
- Clean up temp probe/debug files and zombies after diagnosing; Defender keeps exes locked while a zombie holds them.
