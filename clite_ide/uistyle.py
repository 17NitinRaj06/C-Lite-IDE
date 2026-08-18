"""Shared widget styling helpers (menus, etc.)."""


def style_menu(menu, t):
    """Apply the current theme's colors to a tk.Menu (menubar, dropdown
    and context menus)."""
    menu.configure(
        bg=t["menu_bg"], fg=t["menu_fg"],
        activebackground=t["menu_hover"], activeforeground=t["menu_hover_fg"],
        disabledforeground=t["menu_disabled"],
        selectcolor=t["menu_bg"], relief="flat", bd=0)
