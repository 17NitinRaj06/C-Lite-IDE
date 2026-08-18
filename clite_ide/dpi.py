"""Windows DPI awareness setup.

By default a Windows process is DPI-unaware: Windows renders the whole
app (and any native dialog such as the file picker) at 96 DPI and then
bitmap-stretches it to the display scale, which makes text, icons and
controls look blurry at 125%/150%+ scaling.

Marking the process DPI-aware makes Windows render the UI -- including
the native Open/Save file dialogs -- at the real display DPI, so they
stay sharp at any scale factor.  Must be called before any window is
created (before ``tk.Tk()``).
"""

import sys

try:
    import ctypes
except ImportError:  # pragma: no cover - ctypes is stdlib, always present
    ctypes = None

SYSTEM_DPI_AWARE = 1


def enable_dpi_awareness():
    """Declare the process DPI-aware.  No-op on non-Windows platforms."""
    if sys.platform != "win32" or ctypes is None:
        return
    try:
        # shcore.SetProcessDpiAwareness(PROCESS_SYSTEM_DPI_AWARE) -
        # supported on Windows 8.1+.
        ctypes.windll.shcore.SetProcessDpiAwareness(SYSTEM_DPI_AWARE)
    except (AttributeError, OSError):
        try:
            # Older fallback (Windows Vista+).
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass
