"""Closable file tabs for the editor notebook."""

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

CLOSE_GLYPH = "\u2715"


class ClosableNotebook(ttk.Notebook):
    """ttk.Notebook whose file tabs show a close (X) button.

    The close glyph is embedded in each tab label.  It is always visible
    on the active tab and appears on inactive tabs while hovering over
    them.  Clicking the glyph invokes ``on_close_tab(tab_id)``.

    Tab geometry is computed from the measured label font and the
    notebook's style padding, because ``bbox`` is unreliable across
    Windows themes.
    """

    def __init__(self, master, on_close_tab=None, **kw):
        super().__init__(master, **kw)
        self._base_text = {}
        self._hovered = None
        self.on_close_tab = on_close_tab
        self.bind("<Button-1>", self._on_press)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    # ------------------------------------------------------------------
    #  tab management
    # ------------------------------------------------------------------

    def add_tab(self, frame, text, **kw):
        tab = self.add(frame, text=text, **kw)
        self._base_text[tab] = text
        self._refresh()
        return tab

    def set_label(self, tab, text):
        self._base_text[tab] = text
        self._refresh_tab(tab)

    def forget(self, tab):
        self._base_text.pop(tab, None)
        if self._hovered == tab:
            self._hovered = None
        super().forget(tab)

    # ------------------------------------------------------------------
    #  geometry
    # ------------------------------------------------------------------

    def _tab_font(self):
        try:
            font = self.tk.call("ttk::style", "lookup",
                                "TNotebook.Tab", "font", None, None)
            return tkfont.nametofont(font)
        except tk.TclError:
            return tkfont.nametofont("TkDefaultFont")

    def _tab_padding(self):
        try:
            pad = self.tk.call("ttk::style", "lookup",
                               "TNotebook.Tab", "padding", None, None)
            nums = [int(p) for p in str(pad).split()]
        except (tk.TclError, ValueError):
            nums = []
        if len(nums) == 1:
            return nums[0], nums[0], nums[0], nums[0]
        if len(nums) == 2:
            return nums[0], nums[1], nums[0], nums[1]
        if len(nums) >= 4:
            return nums[0], nums[1], nums[2], nums[3]
        return 8, 3, 8, 3

    def _tab_regions(self):
        """Return {tab_id: (x, y, width, height)} for each tab, wrapping
        tabs into rows when they overflow the notebook width."""
        font = self._tab_font()
        left, top, right, bottom = self._tab_padding()
        strip_width = self.winfo_width()
        regions = {}
        x = 0
        y = 0
        row_height = font.metrics("linespace") + top + bottom + 2
        for tab in self.tabs():
            width = font.measure(self.tab(tab, "text")) + left + right
            if x > 0 and strip_width > 0 and x + width > strip_width:
                x = 0
                y += row_height
            regions[tab] = (x, y, width, row_height)
            x += width
        return regions

    # ------------------------------------------------------------------
    #  label rendering
    # ------------------------------------------------------------------

    def _label_for(self, tab, show_close):
        text = self._base_text.get(tab, "")
        if show_close:
            text += "   " + CLOSE_GLYPH
        return text

    def _refresh_tab(self, tab):
        show = self._shows_close(tab)
        label = self._label_for(tab, show)
        if self.tab(tab, "text") != label:
            self.tab(tab, text=label)

    def _refresh(self):
        sel = self.select()
        for tab in self.tabs():
            show = (tab == sel) or (tab == self._hovered)
            label = self._label_for(tab, show)
            if self.tab(tab, "text") != label:
                self.tab(tab, text=label)

    def _shows_close(self, tab):
        return tab == self.select() or tab == self._hovered

    # ------------------------------------------------------------------
    #  hit testing
    # ------------------------------------------------------------------

    def _tab_at(self, x, y):
        for tab, (tx, ty, tw, th) in self._tab_regions().items():
            if tx <= x < tx + tw and ty <= y < ty + th:
                return tab
        return None

    def _x_region(self, tab):
        regions = self._tab_regions()
        reg = regions.get(tab)
        if not reg:
            return None
        x, y, width, height = reg
        left, top, right, bottom = self._tab_padding()
        font = self._tab_font()
        x_right = x + width - right
        glyph_w = font.measure(CLOSE_GLYPH)
        return x_right - glyph_w - 8, y, x_right + 2, y + height

    # ------------------------------------------------------------------
    #  event handlers
    # ------------------------------------------------------------------

    def _on_press(self, event):
        tab = self._tab_at(event.x, event.y)
        if not tab or not self._shows_close(tab):
            return None
        x_left, y_top, x_right, y_bottom = self._x_region(tab)
        if x_left <= event.x <= x_right and y_top <= event.y <= y_bottom:
            self._hovered = None
            if self.on_close_tab:
                self.on_close_tab(tab)
            return "break"
        return None

    def _on_motion(self, event):
        tab = self._tab_at(event.x, event.y)
        if not tab or tab == self.select():
            self._set_hovered(None)
            return
        self._set_hovered(tab)

    def _on_leave(self, event):
        self._set_hovered(None)

    def _on_tab_changed(self, event):
        self._hovered = None
        self._refresh()

    def _set_hovered(self, tab):
        if tab == self._hovered:
            return
        old = self._hovered
        self._hovered = tab
        if old is not None:
            self._refresh_tab(old)
        if tab is not None:
            self._refresh_tab(tab)