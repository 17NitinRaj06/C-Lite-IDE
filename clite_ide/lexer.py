"""A small C tokenizer used for syntax highlighting.

Colorize(text) returns a list of (start, end, kind) tuples where start/end
are absolute character indices into the text.
"""

import re

KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while",
    "_Bool", "_Complex", "_Imaginary", "_Alignas", "_Alignof", "_Atomic",
    "_Generic", "_Noreturn", "_Static_assert", "_Thread_local",
}

TYPES = {
    "bool", "size_t", "ssize_t", "ptrdiff_t", "intptr_t", "uintptr_t",
    "int8_t", "int16_t", "int32_t", "int64_t", "uint8_t", "uint16_t",
    "uint32_t", "uint64_t", "FILE", "va_list", "wchar_t", "int8_t",
    "time_t", "clock_t", "fpos_t", "div_t", "ldiv_t", "jmp_buf",
}

CONSTANTS = {
    "NULL", "true", "false", "EOF", "DETECT", "TRUE", "FALSE",
    "BLACK", "BLUE", "GREEN", "CYAN", "RED", "MAGENTA", "BROWN",
    "LIGHTGRAY", "DARKGRAY", "LIGHTBLUE", "LIGHTGREEN", "LIGHTCYAN",
    "LIGHTRED", "LIGHTMAGENTA", "YELLOW", "WHITE",
}

_NUM_RE = re.compile(
    r"0[xX][0-9a-fA-F]+[uUlL]*|0[bB][01]+[uUlL]*|\d+\.\d*"
    r"([eE][+-]?\d+)?[fFlL]*|\.\d+([eE][+-]?\d+)?[fFlL]*|"
    r"\d+[eE][+-]?\d+[fFlL]*|\d+[uUlL]*")


def colorize(text):
    out = []
    i = 0
    n = len(text)

    def add(s, e, kind):
        if e > s:
            out.append((s, e, kind))

    while i < n:
        c = text[i]

        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            add(i, j, "comment")
            i = j
            continue

        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            add(i, j, "comment")
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
            add(i, j, "string")
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
            add(i, j, "char")
            i = j
            continue

        if c == "#":
            j = i + 1
            while j < n and text[j] != "\n":
                j += 1
            add(i, j, "preproc")
            i = j
            continue

        if c.isdigit():
            m = _NUM_RE.match(text, i)
            if m:
                add(i, m.end(), "number")
                i = m.end()
                continue

        if c.isalpha() or c == "_":
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            if word in KEYWORDS:
                add(i, j, "keyword")
            elif word in TYPES:
                add(i, j, "type")
            elif word in CONSTANTS:
                add(i, j, "constant")
            else:
                k = j
                while k < n and text[k] in " \t":
                    k += 1
                if k < n and text[k] == "(":
                    add(i, j, "function")
            i = j
            continue

        i += 1

    return out
