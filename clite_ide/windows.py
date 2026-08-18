"""Windows shell integration: AppUserModelID and the C-Lite app icon.

The IDE's official icon is the Tk quill feather (rebuilt from the icon
resources inside tk86t.dll -- the exact artwork Tk shows in the title
bar).  ``icons/app.ico`` is a multi-resolution .ico (16-256 px, PNG
entries for the large sizes); ``icons/app.png`` is the 256px PNG used
as a fallback for :meth:`tkinter.Misc.iconphoto`.

The app icon is wired up in three places:

* ``root.iconbitmap(icon_path())`` -- title bar / Alt+Tab window icon
  while running from source (``python clite.py``).
* A PyInstaller ``--icon`` resource embedded into ``C-Lite IDE.exe``
  (see ``packaging/build_ide.bat``) -- the taskbar, Alt+Tab, the .exe
  icon in Explorer and any shortcuts all pick it up automatically.
* ``SetCurrentProcessExplicitAppUserModelID`` -- associates the process
  with a stable AppUserModelID so Windows groups the IDE's taskbar
  button with the installed app and uses its icon even when the window
  is launched from Python rather than the packaged .exe.

All functions are safe no-ops on non-Windows platforms or when the
icon file is missing.
"""

import os
import sys

try:
    import ctypes
except ImportError:  # pragma: no cover - ctypes is stdlib, always present
    ctypes = None

from . import ROOT

APP_ID = "C-LiteIDE.App"

ICON_FILENAME = "app.ico"
PNG_FILENAME = "app.png"


def _icon_base():
    """Directory containing the icons: the frozen bundle (executable's
    folder) or the project root (running from source)."""
    if getattr(sys, "frozen", False):
        return ROOT
    return os.path.join(ROOT, "icons")


def icon_path():
    """Absolute path to ``icons/app.ico`` (or the frozen bundle copy)."""
    base = _icon_base()
    for candidate in (os.path.join(base, ICON_FILENAME),
                      os.path.join(ROOT, "icons", ICON_FILENAME)):
        if os.path.isfile(candidate):
            return candidate
    return os.path.join(base, ICON_FILENAME)


def png_path():
    """Absolute path to ``icons/app.png`` (or the frozen bundle copy)."""
    base = _icon_base()
    for candidate in (os.path.join(base, PNG_FILENAME),
                      os.path.join(ROOT, "icons", PNG_FILENAME)):
        if os.path.isfile(candidate):
            return candidate
    return os.path.join(base, PNG_FILENAME)


def set_app_user_model_id(appid=None):
    """Associate the process with an AppUserModelID so the taskbar keeps
    the IDE's identity/icon.  Must run before the window is created.
    No-op on non-Windows platforms."""
    if sys.platform != "win32" or ctypes is None:
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            appid or APP_ID)
    except (AttributeError, OSError):
        pass