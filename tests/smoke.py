import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clite_ide.app import App

root = tk.Tk()
app = App(root)
print("startup ok, theme =", app.settings.get("theme"))

root.after(1500, app.show_examples)

def shutdown():
    print("closing...")
    root.destroy()

root.after(3000, shutdown)
root.mainloop()
print("smoke test done")