"""Code editor widget with syntax highlighting, line numbers, folding,
bracket matching, find/replace, undo/redo, go-to-line, auto-closing
brackets/quotes, and smart indentation."""

import os
import re
import tkinter as tk
from tkinter import ttk

from .lexer import colorize
from .settings import THEMES

SYNTAX_KINDS = ("keyword", "type", "string", "char", "number",
                "comment", "preproc", "function", "constant")

# Auto-close pairs
AUTO_CLOSE_PAIRS = {
    "{": "}",
    "(": ")",
    "[": "]",
    '"': '"',
    "'": "'",
}

# Pairs that should not be auto-closed inside strings/comments
STRUCTURAL_PAIRS = {"{": "}", "(": ")", "[": "]"}
QUOTE_PAIRS = {'"': '"', "'": "'"}

# Control statements that expect a block
CONTROL_KEYWORDS = (
    "if", "else", "for", "while", "do", "switch", "catch", "try",
    "finally", "else if", "struct", "class", "enum", "union", "namespace"
)


class Editor(ttk.Frame):
    def __init__(self, master, settings, on_dirty=None, on_cursor=None):
        super().__init__(master)
        self.settings = settings
        self.on_dirty = on_dirty
        self.on_cursor = on_cursor
        self.filepath = None
        self._saved_text = ""
        self._in_refresh = False
        self._folds_cache = {}
        self._folded = set()
        self._find_text = ""
        self._skip_next_modified = False

        self._font = self._make_font()

        # ---- fold gutter (canvas) + line-number gutter ----
        self.fold_canvas = tk.Canvas(self, width=14, bd=0,
                                     highlightthickness=0)
        self.fold_canvas.bind("<Button-1>", self._on_fold_click)
        self.fold_canvas.bind("<MouseWheel>", self._on_wheel)

        self.gutter = tk.Text(self, width=5, wrap="none", state="disabled",
                              bd=0, padx=4, pady=0, font=self._font,
                              cursor="arrow", spacing3=1)
        self.gutter.bind("<MouseWheel>", self._on_wheel)

        # ---- code text ----
        self.content = tk.Text(self, wrap="none", undo=True, bd=0, padx=6,
                               pady=2, font=self._font, spacing3=1,
                               insertwidth=2)
        self.content.configure(takefocus=True)
        self.content.tag_configure("fold", elide=True)
        self.content.tag_configure("find", borderwidth=1, relief="solid")

        self.vscroll = ttk.Scrollbar(self, orient="vertical",
                                     command=self._on_scroll)
        self.hscroll = ttk.Scrollbar(self, orient="horizontal",
                                     command=self.content.xview)
        self.content.configure(yscrollcommand=self._sync_yview,
                               xscrollcommand=self.hscroll.set)

        self.fold_canvas.grid(row=0, column=0, sticky="ns")
        self.gutter.grid(row=0, column=1, sticky="ns")
        self.content.grid(row=0, column=2, sticky="nsew")
        self.vscroll.grid(row=0, column=3, sticky="ns")
        self.hscroll.grid(row=1, column=2, sticky="ew")
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        self._bind_keys()
        self.apply_theme(settings.get("theme", "Light"))
        self._refresh()
        self._notify()

    # ------------------------------------------------------------------
    #  font / theme
    # ------------------------------------------------------------------

    def _make_font(self):
        family = self.settings.get("font_family", "Consolas")
        size = int(self.settings.get("font_size", 11))
        return (family, size)

    def update_font(self):
        self._font = self._make_font()
        self.gutter.configure(font=self._font)
        self.content.configure(font=self._font)

    def apply_theme(self, theme_name):
        t = THEMES.get(theme_name, THEMES["Light"])
        self.content.configure(bg=t["editor_bg"], fg=t["editor_fg"],
                               selectbackground=t["selection_bg"],
                               insertbackground=t["editor_fg"])
        self.content.tag_configure("syn", foreground=t["editor_fg"])
        self.content.tag_configure("linehighlight",
                                   background=t["line_highlight"])
        for kind in SYNTAX_KINDS:
            self.content.tag_configure(kind,
                                       foreground=t["syntax"].get(
                                           kind, t["editor_fg"]))
        self.content.tag_configure("bmatch", background=t["bracket_bg"],
                                   foreground=t["bracket_fg"])
        self.content.tag_configure("find",
                                   background=t["selection_bg"],
                                   foreground=t["editor_fg"])
        self.gutter.configure(bg=t["gutter_bg"], fg=t["gutter_fg"])
        self.fold_canvas.configure(bg=t["gutter_bg"])
        self.fold_canvas.itemconfigure("foldtxt", fill=t["gutter_fg"])

    # ------------------------------------------------------------------
    #  key bindings
    # ------------------------------------------------------------------

    def _bind_keys(self):
        c = self.content
        c.bind("<<Modified>>", self._on_modified)
        c.bind("<<Selection>>", lambda e: self._notify())
        c.bind("<Return>", self._on_return)
        c.bind("<Tab>", self._on_tab)
        c.bind("<Shift-Tab>", self._on_shift_tab)
        c.bind("<KeyRelease>", self._on_keyrelease)
        c.bind("<ButtonRelease-1>", self._on_keyrelease)
        c.bind("<MouseWheel>", self._on_wheel)
        c.bind("<Control-z>", lambda e: self._undo())
        c.bind("<Control-Z>", lambda e: self._undo())
        c.bind("<Control-y>", lambda e: self._redo())
        c.bind("<Control-Y>", lambda e: self._redo())
        c.bind("<Control-Shift-z>", lambda e: self._redo())
        c.bind("<Control-Shift-Z>", lambda e: self._redo())
        c.bind("<F3>", lambda e: self.find_next())

        # Auto-close pairs
        for open_ch, close_ch in AUTO_CLOSE_PAIRS.items():
            c.bind(open_ch, lambda e, oc=open_ch, cc=close_ch: self._on_auto_close(oc, cc))

        # Over-ride closing characters to skip over existing ones
        for close_ch in (")", "]", "}", '"', "'"):
            c.bind(close_ch, lambda e, cc=close_ch: self._on_close_char(cc))

        # Backspace handling for empty pairs
        c.bind("<BackSpace>", self._on_backspace)

    def _on_wheel(self, event):
        delta = -1 if event.delta > 0 else 1
        self.content.yview_scroll(delta, "units")
        self.gutter.yview_moveto(self.content.yview()[0])
        self._redraw_folds()
        return "break"

    def _on_scroll(self, *args):
        self.content.yview(*args)
        self.gutter.yview(*args)
        self._redraw_folds()

    def _sync_yview(self, first, last):
        self.vscroll.set(first, last)
        self.gutter.yview_moveto(first)
        self._redraw_folds()

    # ------------------------------------------------------------------
    #  typing behaviour
    # ------------------------------------------------------------------

    def _on_return(self, event):
        """Smart Enter: handle indentation after {, before }, etc."""
        index = self.content.index("insert")
        line_num = int(index.split(".")[0])
        col = int(index.split(".")[1])

        # Get current line content
        line_start = f"{line_num}.0"
        line_end = f"{line_num}.end"
        line = self.content.get(line_start, line_end)

        # Check if cursor is between { } on same line
        if self._cursor_between_braces(line_num, col):
            # Insert newline, indent, then newline with original indent
            indent = self._get_indent_string()
            base_indent = self._get_base_indent(line)
            self.content.insert("insert", "\n" + base_indent + indent + "\n" + base_indent)
            # Move cursor to the indented middle line
            self.content.mark_set("insert", f"{line_num + 1}.{len(base_indent) + len(indent)}")
            return "break"

        # Check if cursor is at end of line that ends with {
        if self._line_ends_with_open_brace(line, col):
            base_indent = self._get_base_indent(line)
            indent = self._get_indent_string()
            self.content.insert("insert", "\n" + base_indent + indent)
            return "break"

        # Check if cursor is on a line with only } (closing brace)
        if re.match(r"^[ \t]*\}[ \t]*$", line):
            # Find the } position on this line
            brace_col = line.find("}")
            if brace_col >= 0:
                # Find matching { and use its indentation
                match = self._find_matching_open_brace(line_num, brace_col)
                if match:
                    match_line, match_col = match
                    match_line_text = self.content.get(f"{match_line}.0", f"{match_line}.end")
                    base_indent = self._get_base_indent(match_line_text)
                    self.content.insert("insert", "\n" + base_indent)
                    return "break"
            # Fallback: reduce current line's indent
            base_indent = self._get_base_indent(line)
            reduced = self._reduce_indent(base_indent)
            self.content.insert("insert", "\n" + reduced)
            return "break"

        # Default: copy leading whitespace from current line
        m = re.match(r"[ \t]*", line)
        self.content.insert("insert", "\n" + m.group(0))
        return "break"

    def _on_tab(self, event):
        if self.settings.get("use_tabs", False):
            return None
        size = int(self.settings.get("tab_size", 4))
        if self.content.tag_ranges("sel"):
            # Indent selected lines
            return self._indent_selection(size)
        self.content.insert("insert", " " * size)
        return "break"

    def _on_shift_tab(self, event):
        """Shift+Tab to unindent"""
        if self.content.tag_ranges("sel"):
            return self._unindent_selection()
        # Unindent current line
        self._unindent_current_line()
        return "break"

    def _on_auto_close(self, open_ch, close_ch):
        """Auto-insert closing delimiter when opening is typed."""
        # Don't auto-close inside strings or comments
        if self._in_string_or_comment():
            return None

        # For quotes, check if we're continuing a string
        if open_ch in QUOTE_PAIRS:
            if self._should_skip_quote(open_ch):
                return None

        # Insert the pair
        self.content.insert("insert", open_ch + close_ch)
        # Move cursor back between them
        self.content.mark_set("insert", "insert-1c")
        return "break"

    def _on_close_char(self, close_ch):
        """When typing a closing char, skip over it if it's already there."""
        index = self.content.index("insert")
        line_num = int(index.split(".")[0])
        col = int(index.split(".")[1])

        # Check if next character is the same closing char
        next_char = self.content.get(index, f"{index}+1c")
        if next_char == close_ch:
            # Skip over it
            self.content.mark_set("insert", f"{index}+1c")
            return "break"
        return None

    def _on_backspace(self, event):
        """Smart backspace: delete empty pairs together."""
        index = self.content.index("insert")
        line_num = int(index.split(".")[0])
        col = int(index.split(".")[1])

        # Check if cursor is between an empty pair
        if col > 0:
            prev_char = self.content.get(f"{line_num}.{col-1}", f"{line_num}.{col}")
            next_char = self.content.get(index, f"{index}+1c")

            # Check for empty pair: () [] {} "" ''
            if prev_char in AUTO_CLOSE_PAIRS and next_char == AUTO_CLOSE_PAIRS[prev_char]:
                # Delete both characters
                self.content.delete(f"{line_num}.{col-1}", f"{index}+1c")
                return "break"

        return None

    # ------------------------------------------------------------------
    #  Smart indentation helpers
    # ------------------------------------------------------------------

    def _get_indent_string(self):
        """Get the indentation string based on settings."""
        if self.settings.get("use_tabs", False):
            return "\t"
        size = int(self.settings.get("tab_size", 4))
        return " " * size

    def _get_base_indent(self, line):
        """Get the leading whitespace of a line."""
        m = re.match(r"[ \t]*", line)
        return m.group(0) if m else ""

    def _reduce_indent(self, indent):
        """Reduce indentation by one level."""
        if not indent:
            return ""
        indent_str = self._get_indent_string()
        if indent.startswith(indent_str):
            return indent[len(indent_str):]
        # If indent doesn't match expected pattern, remove last 4 spaces or 1 tab
        if indent.startswith(" "):
            return indent[min(4, len(indent)):]
        elif indent.startswith("\t"):
            return indent[1:]
        return ""

    def _cursor_between_braces(self, line_num, col):
        """Check if cursor is between { and } on the same line."""
        line = self.content.get(f"{line_num}.0", f"{line_num}.end")
        if col > 0 and col < len(line):
            return line[col - 1] == "{" and line[col] == "}"
        return False

    def _line_ends_with_open_brace(self, line, col):
        """Check if line ends with { and cursor is at the end."""
        stripped = line.rstrip()
        return stripped.endswith("{") and col >= len(stripped)

    def _indent_selection(self, size):
        """Indent all selected lines."""
        try:
            first = self.content.index("sel.first")
            last = self.content.index("sel.last")
            first_line = int(first.split(".")[0])
            last_line = int(last.split(".")[0])
            indent = " " * size if not self.settings.get("use_tabs", False) else "\t"

            self.content.tag_remove("sel", "1.0", "end")
            for line_num in range(first_line, last_line + 1):
                self.content.insert(f"{line_num}.0", indent)
            self.content.mark_set("insert", f"{first_line}.{len(indent)}")
            self.content.tag_add("sel", f"{first_line}.0", f"{last_line}.end")
        except tk.TclError:
            pass
        return "break"

    def _unindent_selection(self):
        """Unindent all selected lines."""
        try:
            first = self.content.index("sel.first")
            last = self.content.index("sel.last")
            first_line = int(first.split(".")[0])
            last_line = int(last.split(".")[0])

            self.content.tag_remove("sel", "1.0", "end")
            for line_num in range(first_line, last_line + 1):
                line = self.content.get(f"{line_num}.0", f"{line_num}.end")
                indent = self._get_base_indent(line)
                if indent:
                    reduced = self._reduce_indent(indent)
                    self.content.delete(f"{line_num}.0", f"{line_num}.{len(indent)}")
                    self.content.insert(f"{line_num}.0", reduced)
            self.content.tag_add("sel", f"{first_line}.0", f"{last_line}.end")
        except tk.TclError:
            pass
        return "break"

    def _unindent_current_line(self):
        """Unindent the current line."""
        index = self.content.index("insert")
        line_num = int(index.split(".")[0])
        line = self.content.get(f"{line_num}.0", f"{line_num}.end")
        indent = self._get_base_indent(line)
        if indent:
            reduced = self._reduce_indent(indent)
            self.content.delete(f"{line_num}.0", f"{line_num}.{len(indent)}")
            self.content.insert(f"{line_num}.0", reduced)
        return "break"

    def _find_matching_open_brace(self, line_num, col):
        """Find the matching { for a } at the given position."""
        index = f"{line_num}.{col}"
        pos = self._abs_pos_from_index(index)
        text = self.content.get("1.0", "end-1c")
        if pos >= len(text):
            return None
        # We're at a }, find matching {
        depth = 0
        for i in range(pos, -1, -1):
            ch = text[i]
            if ch == "}":
                depth += 1
            elif ch == "{":
                depth -= 1
                if depth == 0:
                    idx = self.content.index(f"1.0+{i}c")
                    parts = idx.split(".")
                    return (int(parts[0]), int(parts[1]))
        return None

    def _in_string_or_comment(self):
        """Check if cursor is inside a string or comment."""
        index = self.content.index("insert")
        pos = self._abs_pos_from_index(index)
        text = self.content.get("1.0", "end-1c")
        # Check current cursor position
        if self._pos_in_string_or_comment(text, pos):
            return True
        # Also check position before cursor (for typing at end of comment/string)
        if pos > 0 and self._pos_in_string_or_comment(text, pos - 1):
            return True
        return False

    def _abs_pos_from_index(self, index):
        """Convert text index to absolute position."""
        line, col = map(int, index.split("."))
        return self._abs_pos(line, col)

    def _pos_in_string_or_comment(self, text, pos):
        """Check if position is inside a string or comment using lexer logic."""
        i = 0
        n = len(text)
        while i < n and i <= pos:
            c = text[i]
            if c == "/" and i + 1 < n and text[i + 1] == "*":
                j = text.find("*/", i + 2)
                j = n if j < 0 else j + 2
                if i <= pos < j:
                    return True
                i = j
                continue
            if c == "/" and i + 1 < n and text[i + 1] == "/":
                j = text.find("\n", i)
                j = n if j < 0 else j
                # Line comment extends to end of line (or end of text)
                # Include cursor at end position
                if i <= pos <= j:
                    return True
                i = j
                continue
            if c == '"':
                j = i + 1
                while j < n:
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text[j] == '"':
                        j += 1
                        break
                    j += 1
                # Handle unclosed string: if no closing quote found, string extends to end
                end_pos = j if j < n else n
                # Include cursor at end of unclosed string (pos == n)
                if i <= pos <= end_pos:
                    return True
                i = j
                continue
            if c == "'":
                j = i + 1
                while j < n:
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text[j] == "'":
                        j += 1
                        break
                    j += 1
                end_pos = j if j < n else n
                if i <= pos <= end_pos:
                    return True
                i = j
                continue
            i += 1
        return False

    def _should_skip_quote(self, quote_char):
        """Check if we should skip auto-closing a quote."""
        index = self.content.index("insert")
        # Check character before cursor
        if index == "1.0":
            return False
        prev_index = f"{index}-1c"
        prev_char = self.content.get(prev_index, index)
        # Don't auto-close if previous char is a backslash (escaped)
        if prev_char == "\\":
            return True
        # Don't auto-close if next char is alphanumeric (continuing a string)
        next_char = self.content.get(index, f"{index}+1c")
        if next_char and (next_char.isalnum() or next_char in "_@"):
            return True
        return False

    def _undo(self):
        try:
            self.content.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def _redo(self):
        try:
            self.content.edit_redo()
        except tk.TclError:
            pass
        return "break"

    def _on_keyrelease(self, event):
        if event.keysym in ("Return",):
            return
        self._match_bracket()
        self._update_line_highlight()
        self._notify()

    # ------------------------------------------------------------------
    #  modification handling
    # ------------------------------------------------------------------

    def _on_modified(self, event=None):
        if self._in_refresh:
            return
        self._in_refresh = True
        try:
            self._update_gutter()
            self._highlight()
            self._update_folds_cache()
            self._redraw_folds()
            self._match_bracket()
            self._update_line_highlight()
            self._notify()
        finally:
            self._in_refresh = False
            self.content.edit_modified(False)

    def _notify(self):
        if self.on_cursor:
            line = int(self.content.index("insert").split(".")[0])
            col = int(self.content.index("insert").split(".")[1])
            self.on_cursor(self, line, col)
        if self.on_dirty:
            self.on_dirty(self, self.is_dirty())

    def _highlight(self):
        text = self.content.get("1.0", "end-1c")
        self.content.tag_remove("syn", "1.0", "end")
        for kind in SYNTAX_KINDS:
            self.content.tag_remove(kind, "1.0", "end")
        for start, end, kind in colorize(text):
            self.content.tag_add(kind, f"1.0+{start}c", f"1.0+{end}c")

    def _update_gutter(self):
        nlines = int(self.content.index("end-1c").split(".")[0])
        self.gutter.configure(state="normal")
        self.gutter.delete("1.0", "end")
        if nlines > 0:
            nums = "\n".join(str(i) for i in range(1, nlines + 1))
            self.gutter.insert("1.0", nums)
        self.gutter.configure(state="disabled")
        self._apply_fold_tags_to_gutter()

    def _apply_fold_tags_to_gutter(self):
        self.gutter.tag_remove("fold", "1.0", "end")
        for header in self._folded:
            close = self._folds_cache.get(header)
            if close:
                self.gutter.tag_add("fold", f"{header + 1}.0",
                                    f"{close}.0")

    # ------------------------------------------------------------------
    #  folding
    # ------------------------------------------------------------------

    def _update_folds_cache(self):
        text = self.content.get("1.0", "end-1c")
        lines = text.split("\n")
        stack = []
        folds = {}
        for idx, line in enumerate(lines, 1):
            for ch in line:
                if ch == "{":
                    stack.append(idx)
                elif ch == "}":
                    if stack:
                        o = stack.pop()
                        if idx - o >= 1 and o not in folds:
                            folds[o] = idx
        self._folds_cache = folds
        self._folded = {h for h in self._folded if h in folds}

    def toggle_fold(self, line):
        close = self._folds_cache.get(line)
        if not close:
            return
        if line in self._folded:
            self.content.tag_remove("fold", f"{line + 1}.0", f"{close}.0")
            self.gutter.tag_remove("fold", f"{line + 1}.0", f"{close}.0")
            self._folded.discard(line)
        else:
            self.content.tag_add("fold", f"{line + 1}.0", f"{close}.0")
            self.gutter.tag_add("fold", f"{line + 1}.0", f"{close}.0")
            self._folded.add(line)
        self._redraw_folds()
        self._notify()

    def _line_at_y(self, y):
        nlines = int(self.content.index("end-1c").split(".")[0])
        for i in range(1, nlines + 1):
            d = self.content.dlineinfo(f"{i}.0")
            if d is None:
                continue
            dy, dh = d[1], d[3]
            if dy <= y < dy + dh:
                return i
        return None

    def _redraw_folds(self):
        self.fold_canvas.delete("all")
        if not self.winfo_viewable():
            return
        height = self.fold_canvas.winfo_height()
        nlines = int(self.content.index("end-1c").split(".")[0])
        for i in range(1, nlines + 1):
            d = self.content.dlineinfo(f"{i}.0")
            if d is None:
                continue
            y, dh = d[1], d[3]
            if y > height:
                break
            if i in self._folds_cache:
                marker = "\u2212" if i in self._folded else "+"
                self.fold_canvas.create_text(
                    7, y + dh // 2, text=marker,
                    tags=("foldtxt",), font=self._font)

    def _on_fold_click(self, event):
        line = self._line_at_y(event.y)
        if line:
            self.toggle_fold(line)

    def fold_all(self):
        self._update_folds_cache()
        for header in self._folds_cache:
            if header not in self._folded:
                self.toggle_fold(header)

    def unfold_all(self):
        for header in list(self._folded):
            self.toggle_fold(header)

    # ------------------------------------------------------------------
    #  bracket matching
    # ------------------------------------------------------------------

    def _match_bracket(self):
        self.content.tag_remove("bmatch", "1.0", "end")
        idx = self.content.index("insert")
        line = int(idx.split(".")[0])
        char = int(idx.split(".")[1])
        pairs = {"(": ")", "{": "}", "[": "]",
                 ")": "(", "}": "{", "]": "["}
        for pos in (char - 1, char):
            ch = self.content.get(f"{line}.{pos}", f"{line}.{pos + 1}")
            if ch in pairs:
                m = self._find_match(line, pos, pairs[ch])
                if m:
                    self.content.tag_add("bmatch", f"{line}.{pos}",
                                         f"{line}.{pos + 1}")
                    self.content.tag_add("bmatch", f"{m[0]}.{m[1]}",
                                         f"{m[0]}.{m[1] + 1}")
                return

    def _abs_pos(self, line, char):
        txt = self.content.get("1.0", f"{line}.{char}")
        return len(txt)

    def _find_match(self, line, char, target):
        text = self.content.get("1.0", "end-1c")
        pos = self._abs_pos(line, char)
        open_ch = text[pos] if pos < len(text) else ""
        depth = 0
        if open_ch in "([{":
            for i in range(pos, len(text)):
                if text[i] == open_ch:
                    depth += 1
                elif text[i] == target:
                    depth -= 1
                    if depth == 0:
                        idx = self.content.index(f"1.0+{i}c")
                        parts = idx.split(".")
                        return (int(parts[0]), int(parts[1]))
        else:
            for i in range(pos, -1, -1):
                if text[i] == open_ch:
                    depth += 1
                elif text[i] == target:
                    depth -= 1
                    if depth == 0:
                        idx = self.content.index(f"1.0+{i}c")
                        parts = idx.split(".")
                        return (int(parts[0]), int(parts[1]))
        return None

    # ------------------------------------------------------------------
    #  line highlight / navigation
    # ------------------------------------------------------------------

    def _update_line_highlight(self):
        self.content.tag_remove("linehighlight", "1.0", "end")
        idx = self.content.index("insert")
        line = idx.split(".")[0]
        self.content.tag_add("linehighlight", f"{line}.0",
                             f"{line}.end")

    def goto_line(self, line, col=0):
        line = max(1, line)
        nlines = int(self.content.index("end-1c").split(".")[0])
        line = min(line, nlines)
        self.content.mark_set("insert", f"{line}.{col}")
        self.content.see(f"{line}.0")
        self.content.focus_set()
        self._match_bracket()
        self._update_line_highlight()
        self._notify()

    # ------------------------------------------------------------------
    #  find / replace
    # ------------------------------------------------------------------

    def find(self, text, forward=True):
        if not text:
            return False
        self._find_text = text
        self.content.tag_remove("find", "1.0", "end")
        start = self.content.index("sel.first") if self.content.tag_ranges(
            "sel") else None
        if forward:
            if not start:
                start = self.content.index("insert")
            found = self.content.search(text, start, nocase=1,
                                        stopindex="end")
            if not found:
                found = self.content.search(text, "1.0", nocase=1,
                                            stopindex="end")
        else:
            if not start:
                start = self.content.index("insert")
            found = self.content.search(text, start, nocase=1,
                                        backwards=True, stopindex="1.0")
            if not found:
                found = self.content.search(text, "end", nocase=1,
                                            backwards=True,
                                            stopindex="1.0")
        if found:
            self.content.tag_add("find", found,
                                 f"{found}+{len(text)}c")
            self.content.tag_add("sel", found, f"{found}+{len(text)}c")
            self.content.mark_set("insert", found)
            self.content.see(found)
            return True
        return False

    def find_next(self, event=None):
        return self.find(self._find_text or
                         self.content.get("sel.first", "sel.last"), True)

    def find_prev(self, event=None):
        return self.find(self._find_text or
                         self.content.get("sel.first", "sel.last"), False)

    def replace(self, text, repl):
        if not text:
            return False
        if self.content.tag_ranges("sel"):
            sel = self.content.get("sel.first", "sel.last")
            if sel == text:
                self.content.delete("sel.first", "sel.last")
                self.content.insert("sel.first", repl)
        found = self.find(text, True)
        return bool(found)

    def replace_all(self, text, repl):
        if not text:
            return 0
        count = 0
        while True:
            self.content.tag_remove("sel", "1.0", "end")
            found = self.content.search(text, "insert", nocase=1,
                                        stopindex="end")
            if not found:
                found = self.content.search(text, "1.0", nocase=1,
                                            stopindex="insert")
            if not found:
                break
            self.content.delete(found, f"{found}+{len(text)}c")
            self.content.insert(found, repl)
            self.content.mark_set("insert", found)
            count += 1
        self.content.tag_remove("find", "1.0", "end")
        return count

    def highlight_all(self, text):
        self.content.tag_remove("find", "1.0", "end")
        if not text:
            return
        idx = "1.0"
        while True:
            idx = self.content.search(text, idx, nocase=1,
                                      stopindex="end")
            if not idx:
                break
            self.content.tag_add("find", idx, f"{idx}+{len(text)}c")
            idx = f"{idx}+{len(text)}c"

    # ------------------------------------------------------------------
    #  file / text access
    # ------------------------------------------------------------------

    def set_text(self, text, filepath=None):
        self.content.delete("1.0", "end")
        self.content.insert("1.0", text)
        self.filepath = filepath
        self._saved_text = text
        self.content.edit_reset()
        self._folded = set()
        self._in_refresh = True
        self.content.edit_modified(False)
        self._in_refresh = False
        self._refresh()
        self._update_gutter()
        self.goto_line(1)

    def get_text(self):
        return self.content.get("1.0", "end-1c")

    def is_dirty(self):
        return self.get_text() != self._saved_text

    def mark_saved(self):
        self._saved_text = self.get_text()
        self._notify()

    def load_file(self, path):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        self.set_text(text, path)

    def save_file(self, path):
        text = self.get_text()
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        self.filepath = path
        self.mark_saved()
        return True

    def _refresh(self):
        self._update_gutter()
        self._highlight()
        self._update_folds_cache()
        self._redraw_folds()
        self._match_bracket()
        self._update_line_highlight()

    def get_line_count(self):
        return int(self.content.index("end-1c").split(".")[0])

    def display_name(self):
        if self.filepath:
            return os.path.basename(self.filepath)
        return "Untitled"

    def focus(self):
        self.content.focus_set()


class FindBar(ttk.Frame):
    """Compact find / replace bar attached to an editor."""

    def __init__(self, master, editor):
        super().__init__(master)
        self.editor = editor

        self.lbl_find = ttk.Label(self, text="Find:")
        self.ent_find = ttk.Entry(self, width=22)
        self.btn_prev = ttk.Button(self, text="\u2191", width=3,
                                   command=editor.find_prev)
        self.btn_next = ttk.Button(self, text="\u2193", width=3,
                                   command=editor.find_next)
        self.lbl_repl = ttk.Label(self, text="Replace:")
        self.ent_repl = ttk.Entry(self, width=22)
        self.btn_repl = ttk.Button(self, text="Replace", width=8,
                                   command=self.do_replace)
        self.btn_all = ttk.Button(self, text="All", width=4,
                                  command=self.do_replace_all)
        self.btn_close = ttk.Button(self, text="\u2715", width=3,
                                    command=self.hide)

        self.ent_find.bind("<Return>", lambda e: editor.find_next())
        self.ent_find.bind("<Escape>", lambda e: self.hide())
        self.ent_repl.bind("<Return>", lambda e: self.do_replace())
        self.ent_repl.bind("<Escape>", lambda e: self.hide())

        self.grid_columnconfigure(1, weight=1)
        self._build()

    def _build(self):
        self.lbl_find.grid(row=0, column=0, padx=(8, 3), pady=2)
        self.ent_find.grid(row=0, column=1, sticky="ew", pady=2)
        self.btn_prev.grid(row=0, column=2, padx=1, pady=2)
        self.btn_next.grid(row=0, column=3, padx=1, pady=2)
        self.lbl_repl.grid(row=0, column=4, padx=(10, 3), pady=2)
        self.ent_repl.grid(row=0, column=5, sticky="ew", pady=2)
        self.btn_repl.grid(row=0, column=6, padx=1, pady=2)
        self.btn_all.grid(row=0, column=7, padx=1, pady=2)
        self.btn_close.grid(row=0, column=8, padx=(4, 8), pady=2)

    def show_find(self):
        self.lbl_repl.grid_remove()
        self.ent_repl.grid_remove()
        self.btn_repl.grid_remove()
        self.btn_all.grid_remove()
        self.grid()
        self.ent_find.focus_set()
        self.ent_find.select_range(0, "end")
        self.editor.content.tag_remove("sel", "1.0", "end")

    def show_replace(self):
        self.lbl_repl.grid()
        self.ent_repl.grid()
        self.btn_repl.grid()
        self.btn_all.grid()
        self.grid()
        self.ent_find.focus_set()
        self.ent_find.select_range(0, "end")

    def hide(self):
        self.grid_remove()
        self.editor.content.focus_set()
        self.editor.content.tag_remove("find", "1.0", "end")

    def do_replace(self):
        text = self.ent_find.get()
        repl = self.ent_repl.get()
        self.editor.replace(text, repl)

    def do_replace_all(self):
        text = self.ent_find.get()
        repl = self.ent_repl.get()
        n = self.editor.replace_all(text, repl)
        self.editor.content.focus_set()
