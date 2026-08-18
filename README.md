# C-Lite IDE

A lightweight C/C++ IDE for Windows, designed for students learning C with Turbo C / Borland-era workflow. C-Lite provides a complete offline development environment with a bundled MinGW compiler, Turbo C-compatible `graphics.h` and `conio.h` implementations, and a familiar tabbed editor interface.

**Version:** 1.0.0

## Features

- **Code Editor** — Tabbed interface with syntax highlighting for C/C++, line numbers, find/replace, go to line, code folding
- **Syntax Highlighting** — Configurable themes (Light/Dark) with C/C++ syntax coloring
- **Project/File Explorer** — Lazy-loaded tree view with file operations (new, rename, delete, refresh), active file highlighting
- **Compile & Run** — One-click build (F6) and compile-and-run (F5) with automatic dependency tracking
- **Integrated Terminal** — Program I/O with stdin support for interactive programs
- **Compile Log** — Dedicated panel showing exact compiler command, raw output, elapsed time, and success/failure summary
- **Problems Panel** — Parsed errors/warnings with click-to-navigate
- **C/C++ Support** — Auto-detects `.c`/`.cpp`/`.cc`/`.cxx` files, uses `gcc`/`g++` appropriately
- **Graphics Support** — Full `graphics.h` / BGI compatibility via native Windows GDI runtime (`line`, `circle`, `rectangle`, `bar`, `ellipse`, `floodfill`, `drawpoly`, `fillpoly`, `pieslice`, `sector`, text output, viewports, palettes, etc.)
- **Conio Support** — `getch()`, `kbhit()`, `clrscr()`, `gotoxy()`, `textColor()`, `textBackground()`, `cprintf()`, `delay()`, `sound()`, `nosound()` — works in both real console and IDE terminal
- **Turbo C Compatibility** — Accepts `void main()`, historical `initgraph(&gd, &gm, "C:\\TURBOC3\\BGI")` path (ignored), classic 16-color palette constants
- **Dark Theme** — Cohesive charcoal color scheme across editor, explorer, terminal, tabs, dialogs
- **DPI Awareness** — Native rendering at 125%/150%/200% scaling (no blurry file dialogs)
- **Official Icon** — Tk feather icon embedded in exe, taskbar, Alt+Tab, Explorer
- **Fully Offline** — Bundled 32-bit MinGW GCC 6.3.0, no internet required after download
- **Portable** — Single `.exe` distribution with all dependencies self-contained

## Requirements

### Running from Source
- Windows 10/11 (x64)
- Python 3.10+ (tested on 3.13) with `tkinter` (standard library)
- No additional Python packages required

### Packaged Executable
- Windows 10/11 (x64)
- No Python installation needed — completely self-contained

## Running from Source

```cmd
cd C-Lite-IDE
python clite.py
```

Or use the launcher:
```cmd
start.bat
```

## Building the Executable

The project includes a complete PyInstaller build pipeline.

### Prerequisites
```cmd
pip install pyinstaller
```

### Build
```cmd
cd packaging
build_ide.bat
```

Output: `dist\C-Lite IDE\C-Lite IDE.exe` with `compiler/`, `include/`, `runtime/`, `examples/`, `icons/` copied alongside for a fully self-contained offline distribution.

The build script:
1. Compiles `packaging/app.rc` with the bundled `windres` (embeds icon + version resource)
2. Runs PyInstaller with `--onedir --windowed --icon icons\app.ico`
3. Copies all runtime dependencies next to the exe

## Project Structure

```
C-Lite-IDE/
├── clite_ide/           # Main application package
│   ├── app.py           # Main window, editor tabs, menus, toolchain glue
│   ├── builder.py       # GCC invocation, runtime object compilation, Defender warm-up
│   ├── runner.py        # Background process launch with stop guard
│   ├── tabs.py          # ClosableNotebook with X button per tab
│   ├── editor.py        # Syntax-highlighting editor with find/replace
│   ├── explorer.py      # Project/File explorer (lazy tree, file ops)
│   ├── terminal.py      # Integrated terminal (program I/O)
│   ├── compilelog.py    # Compile Log panel
│   ├── problems.py      # Problems panel (parsed errors/warnings)
│   ├── project.py       # Project model (.cliteproject)
│   ├── settings.py      # Themes, settings persistence, compiler discovery
│   ├── dialogs.py       # Themed dialog replacements (ask_string, ask_yes_no, etc.)
│   ├── uistyle.py       # Shared ttk menu styling
│   ├── dpi.py           # DPI awareness bootstrap
│   ├── windows.py       # AppUserModelID, icon path resolution
│   ├── lexer.py         # C/C++ syntax highlighter
│   ├── examples.py      # Built-in examples catalog
│   └── __init__.py      # Path constants (ROOT, INCLUDE_DIR, RUNTIME_DIR, etc.)
├── compiler/
│   └── mingw/           # Bundled 32-bit MinGW GCC 6.3.0 (bin, include, lib, libexec, share)
├── include/             # C headers: graphics.h, conio.h, dos.h
├── runtime/             # C runtime sources (compiled & linked automatically)
│   ├── bgilite.c        # Win32 GDI implementation of BGI graphics.h
│   ├── conio_lite.c     # Console I/O (getch, clrscr, gotoxy, etc.)
│   └── clite_startup.c  # Unbuffered stdout/stderr before main()
├── examples/
│   ├── console/         # Console programs (hello_world, fibonacci, etc.)
│   └── graphics/        # Graphics demos (dda_line, circle, shapes, transformations)
├── icons/
│   ├── app.ico          # Multi-resolution Windows icon (16-256px)
│   └── app.png          # 256px PNG (runtime iconphoto fallback)
├── packaging/
│   ├── build_ide.bat    # Build pipeline (windres + PyInstaller + copy deps)
│   ├── app.rc           # Version resource + icon
│   └── make_icon.py     # Regenerates icons from tk86t.dll feather resources
├── tests/               # Development test suite
│   ├── test_tabs.py
│   ├── test_close_state.py
│   ├── test_dialog_center.py
│   ├── test_statusbar.py
│   ├── test_explorer.py
│   ├── smoke.py
│   ├── e2e.py
│   └── input_test.py
├── clite.py             # Entry point
├── settings.json        # User settings (created on first run)
├── C-Lite IDE.spec      # PyInstaller spec (minimal; build_ide.bat is authoritative)
├── start.bat            # Quick launcher (pythonw fallback to python)
├── CONTEXT.md           # Project context for AI assistants
└── README.md            # This file
```

## C-Lite Compiler & Runtime

### Bundled Toolchain
C-Lite ships with **MinGW.org GCC 6.3.0 (32-bit)** — the exact build the BGI runtime was developed against. The toolchain lives at `compiler/mingw/` and includes:
- `bin/gcc.exe`, `g++.exe`, `ar.exe`, `ld.exe`, `as.exe`, `windres.exe`
- Runtime DLLs: `libgcc_s_dw2-1.dll`, `libstdc++-6.dll`, `libgmp-10.dll`, `libmpfr-4.dll`, `libmpc-3.dll`
- Standard headers in `include/`, libraries in `lib/`

### Compiler Discovery Priority
1. Bundled `compiler\mingw\bin\gcc.exe`
2. User-configured path in View → Settings → GCC path
3. `gcc` on system PATH
4. Common install locations (`C:\MinGW`, `C:\mingw64`, TDM-GCC, MSYS2)

### Build Process
- Runtime sources (`bgilite.c`, `conio_lite.c`, `clite_startup.c`) are compiled to `.o` files once per build directory and reused
- Graphics programs link with `-lgdi32 -lm` (no `graphics.lib`/`libbgi.a` needed)
- `clite_startup.c` runs before `main()` and makes stdout/stderr unbuffered for instant terminal output
- Windows Defender first-run scan is triggered **during compilation** (`builder._warm_exe()`) so the first Run is instant

### Graphics Runtime (`bgilite.c`)
- Re-implements Turbo C BGI using native Windows GDI
- Double-buffered drawing to an in-memory bitmap, blitted to a dedicated top-level window
- `initgraph()` ignores the historical driver path — no BGI files required
- Runs the graphics window on a separate thread; main thread pumps messages to avoid deadlock
- Implements the full classic API: primitives, viewports, palettes, text, image operations, flood fill, polygons, arcs, ellipses, bar3d, pieslice, sector

### Conio Runtime (`conio_lite.c`)
- Dual-mode: native Windows console APIs when attached to a real console; stdio fallback when piped (IDE terminal)
- `getch()`/`kbhit()` work correctly after `scanf()` (skips leftover newlines)
- `clrscr()`, `gotoxy()`, `textColor()`, `textBackground()`, `cprintf()`, `delay()`, `sound()`, `nosound()`

## Testing

Run the test suite from the project root:

```cmd
python tests\test_tabs.py
python tests\test_close_state.py
python tests\test_dialog_center.py
python tests\test_statusbar.py
python tests\test_explorer.py
python tests\smoke.py
python tests\e2e.py
python tests\input_test.py
```

**Note:** Set `PYTHONIOENCODING=utf-8` if running in a console that doesn't support the ✕ glyph (cp1252).

## License

**LICENSE NOT SELECTED** — This project does not currently have a license. Choose an appropriate open-source license (MIT, BSD-3-Clause, GPL-3.0, etc.) before public distribution.

## Installation

### Using the Installer (Recommended for End Users)

1. Download the latest `C-Lite-IDE-Setup-<version>.exe` from the [GitHub Releases](https://github.com/YOUR_GITHUB_USERNAME/C-Lite-IDE/releases) page.
2. Double-click the installer to launch the setup wizard.
3. Follow the on-screen instructions:
   - Choose installation directory (default: `C:\Program Files\C-Lite IDE\`)
   - Optionally create a Desktop shortcut
4. Click **Install** to begin installation.
5. After installation completes, launch C-Lite IDE from the Start Menu or Desktop shortcut.

The installer includes:
- C-Lite IDE application
- Bundled MinGW GCC 6.3.0 compiler
- C headers (`graphics.h`, `conio.h`, `dos.h`)
- BGI graphics runtime
- Example programs
- Application icon

### Uninstalling

- **Via Windows Settings:** Settings → Apps → Installed apps → C-Lite IDE → Uninstall
- **Via Start Menu:** Start Menu → C-Lite IDE → Uninstall C-Lite IDE

The uninstaller removes all application files, the bundled compiler, and shortcuts. Your personal projects are not deleted.

## Building from Source

### Prerequisites

- Windows 10/11 (x64)
- Python 3.10+ with `tkinter` (standard library)
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (for creating the installer)
- `pyinstaller` Python package

```cmd
pip install pyinstaller
```

### Building the Executable

```cmd
cd packaging
build_ide.bat
```

Output: `dist\C-Lite IDE\C-Lite IDE.exe` with all dependencies copied alongside.

### Building the Installer

```cmd
cd packaging
build_release.bat
```

Output: `release\C-Lite-IDE-Setup-<version>.exe`

The release build script:
1. Reads version from `version.txt`
2. Cleans previous build output
3. Builds the executable via `build_ide.bat`
4. Generates Inno Setup script with version
5. Compiles installer with Inno Setup
6. Outputs to `release\` directory

## Creating a Release

To create a new release (e.g., version 1.1.0):

1. **Update version:**
   Edit `version.txt`:
   ```
   1.1.0
   ```

2. **Update GitHub configuration:**
   Edit `github_config.ini` with your GitHub username:
   ```
   GITHUB_OWNER = your-github-username
   GITHUB_REPO = C-Lite-IDE
   ```

3. **Test the build:**
   ```cmd
   packaging\build_release.bat
   ```

4. **Verify the installer:**
   - Run `release\C-Lite-IDE-Setup-1.1.0.exe`
   - Install and test C-Lite IDE
   - Verify compiler, graphics, terminal all work
   - Test uninstaller

5. **Commit and tag:**
   ```cmd
   git add version.txt github_config.ini
   git commit -m "Release C-Lite IDE 1.1.0"
   git push
   git tag v1.1.0
   git push origin v1.1.0
   ```

6. **Create GitHub Release:**
   - Go to GitHub Releases page
   - Click "Create a new release"
   - Select tag `v1.1.0`
   - Title: `C-Lite IDE 1.1.0`
   - Upload `release\C-Lite-IDE-Setup-1.1.0.exe`
   - Publish release

## Update System

C-Lite IDE includes a built-in update checker:

**Help → Check for Updates**

This queries the GitHub Releases API and compares the installed version with the latest release. If a newer version is available, it shows:
- Current version vs. latest version
- Release notes
- Buttons to view release page or download the installer

## Versioning

C-Lite IDE uses [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

Examples:
- `1.0.0` — Initial release
- `1.0.1` — Bug fixes
- `1.1.0` — New features (backward compatible)
- `2.0.0` — Breaking changes

The version is stored in `version.txt` and automatically used by:
- Application (window title, About dialog)
- PyInstaller build (executable version resource)
- Inno Setup installer (installer version, output filename)
- Update checker (comparison with GitHub Releases)

## Acknowledgments

- **Tkinter** — The feather icon is extracted from `tk86t.dll` (Tcl/Tk)
- **MinGW.org** — Bundled GCC 6.3.0 toolchain
- **Windows GDI** — Powers the BGI graphics compatibility layer
- **Inno Setup** — Professional Windows installer