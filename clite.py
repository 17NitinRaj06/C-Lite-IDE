"""C-Lite IDE entry point.

Run with:  python clite.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clite_ide.dpi import enable_dpi_awareness
from clite_ide.windows import set_app_user_model_id

enable_dpi_awareness()
set_app_user_model_id()

from clite_ide.app import main

if __name__ == "__main__":
    main()