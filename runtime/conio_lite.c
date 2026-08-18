/*
 *  conio_lite.c - C-Lite conio runtime.
 *
 *  Implements the Turbo C console I/O functions declared in
 *  include/conio.h.  Two modes are supported:
 *
 *    - When the program runs from a real Windows console, the native
 *      console functions are used so clrscr(), gotoxy(), textcolor(),
 *      getch() etc. behave like Turbo C.
 *
 *    - When the program runs inside the C-Lite IDE terminal (stdin /
 *      stdout are pipes, no console attached) a stdio based fallback is
 *      used so the same functions keep working.
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <io.h>

#include "conio.h"

/* current text attributes */
static int g_text_fg = 7;  /* light gray */
static int g_text_bg = 0;  /* black */
static int g_text_hi = 0;

static int g_win_x1 = 1, g_win_y1 = 1, g_win_x2 = 80, g_win_y2 = 25;

static int clite_have_console(void)
{
    HANDLE h = GetStdHandle(STD_INPUT_HANDLE);
    DWORD mode;
    return h != INVALID_HANDLE_VALUE && h != NULL &&
           GetConsoleMode(h, &mode);
}

static HANDLE clite_std_out(void)
{
    HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
    return (h == INVALID_HANDLE_VALUE) ? NULL : h;
}

static WORD clite_attr(void)
{
    WORD a = 0;
    int fg = g_text_fg & 0x0F;
    int bg = g_text_bg & 0x07;
    a = (WORD)(bg << 4);
    a |= (WORD)((g_text_hi ? 8 : 0) | fg);
    return a;
}

/* ------------------------------------------------------------------ */
/*  character input                                                    */
/* ------------------------------------------------------------------ */

static int clite_read_pipe_char(int echo)
{
    int c;
    /* read through the shared stdio buffer (same stream scanf uses) and
       skip CR/LF so getch() after scanf() waits for a real keypress */
    do {
        c = fgetc(stdin);
        if (c == EOF)
            return 0;
    } while (c == '\r' || c == '\n');
    if (echo)
        putchar(c);
    return c;
}

static int clite_read_console_char(int echo)
{
    HANDLE h = GetStdHandle(STD_INPUT_HANDLE);
    DWORD old_mode, mode, n = 0;
    char buf[16];
    int ch = 0;
    if (h == INVALID_HANDLE_VALUE || !h)
        return 0;
    GetConsoleMode(h, &old_mode);
    mode = old_mode & ~(ENABLE_ECHO_INPUT | ENABLE_LINE_INPUT);
    SetConsoleMode(h, mode);
    ReadConsoleA(h, buf, 1, &n, NULL);
    SetConsoleMode(h, old_mode);
    if (n > 0)
        ch = (unsigned char)buf[0];
    if (echo && ch)
        putchar(ch);
    return ch;
}

int getch(void)
{
    if (clite_have_console())
        return clite_read_console_char(0);
    return clite_read_pipe_char(0);
}

int getche(void)
{
    if (clite_have_console())
        return clite_read_console_char(1);
    return clite_read_pipe_char(1);
}

int kbhit(void)
{
    HANDLE h;
    if (clite_have_console()) {
        DWORD n = 0;
        HANDLE in = GetStdHandle(STD_INPUT_HANDLE);
        GetNumberOfConsoleInputEvents(in, &n);
        return n > 0;
    }
    h = GetStdHandle(STD_INPUT_HANDLE);
    if (h == INVALID_HANDLE_VALUE || !h)
        return 0;
    {
        DWORD avail = 0;
        if (PeekNamedPipe(h, NULL, 0, NULL, &avail, NULL))
            return avail > 0;
    }
    return 0;
}

/* ------------------------------------------------------------------ */
/*  screen / cursor control                                            */
/* ------------------------------------------------------------------ */

void clrscr(void)
{
    HANDLE h = clite_std_out();
    COORD home = {0, 0};
    DWORD written, cells;
    CONSOLE_SCREEN_BUFFER_INFO info;
    if (h && GetConsoleScreenBufferInfo(h, &info)) {
        cells = (DWORD)(info.dwSize.X * info.dwSize.Y);
        FillConsoleOutputCharacterA(h, ' ', cells, home, &written);
        FillConsoleOutputAttribute(h, clite_attr(), cells, home, &written);
        SetConsoleCursorPosition(h, home);
    }
}

void clreol(void)
{
    HANDLE h = clite_std_out();
    DWORD written;
    CONSOLE_SCREEN_BUFFER_INFO info;
    if (h && GetConsoleScreenBufferInfo(h, &info)) {
        COORD start = info.dwCursorPosition;
        DWORD cells = (DWORD)(info.dwSize.X - start.X);
        FillConsoleOutputCharacterA(h, ' ', cells, start, &written);
        FillConsoleOutputAttribute(h, clite_attr(), cells, start, &written);
    }
}

void gotoxy(int x, int y)
{
    HANDLE h = clite_std_out();
    COORD c;
    if (x < g_win_x1) x = g_win_x1;
    if (x > g_win_x2) x = g_win_x2;
    if (y < g_win_y1) y = g_win_y1;
    if (y > g_win_y2) y = g_win_y2;
    c.X = (SHORT)(x - 1);
    c.Y = (SHORT)(y - 1);
    if (h)
        SetConsoleCursorPosition(h, c);
}

void window(int left, int top, int right, int bottom)
{
    g_win_x1 = left; g_win_y1 = top;
    g_win_x2 = right; g_win_y2 = bottom;
}

int wherex(void)
{
    HANDLE h = clite_std_out();
    CONSOLE_SCREEN_BUFFER_INFO info;
    if (h && GetConsoleScreenBufferInfo(h, &info))
        return info.dwCursorPosition.X + 1;
    return 1;
}

int wherey(void)
{
    HANDLE h = clite_std_out();
    CONSOLE_SCREEN_BUFFER_INFO info;
    if (h && GetConsoleScreenBufferInfo(h, &info))
        return info.dwCursorPosition.Y + 1;
    return 1;
}

void insline(void)
{
    HANDLE h = clite_std_out();
    CONSOLE_SCREEN_BUFFER_INFO info;
    SMALL_RECT scroll;
    COORD dest;
    CHAR_INFO fill;
    if (h && GetConsoleScreenBufferInfo(h, &info)) {
        scroll.Top = info.dwCursorPosition.Y;
        scroll.Bottom = info.dwSize.Y - 1;
        scroll.Left = 0;
        scroll.Right = info.dwSize.X - 1;
        dest.X = 0;
        dest.Y = info.dwCursorPosition.Y + 1;
        fill.Char.AsciiChar = ' ';
        fill.Attributes = clite_attr();
        ScrollConsoleScreenBufferA(h, &scroll, NULL, dest, &fill);
    }
}

void delline(void)
{
    HANDLE h = clite_std_out();
    CONSOLE_SCREEN_BUFFER_INFO info;
    SMALL_RECT scroll;
    COORD dest;
    CHAR_INFO fill;
    if (h && GetConsoleScreenBufferInfo(h, &info)) {
        scroll.Top = info.dwCursorPosition.Y + 1;
        scroll.Bottom = info.dwSize.Y - 1;
        scroll.Left = 0;
        scroll.Right = info.dwSize.X - 1;
        dest.X = 0;
        dest.Y = info.dwCursorPosition.Y;
        fill.Char.AsciiChar = ' ';
        fill.Attributes = clite_attr();
        ScrollConsoleScreenBufferA(h, &scroll, NULL, dest, &fill);
    }
}

void textmode(int mode) { (void)mode; }

void movetext(int left, int top, int right, int bottom,
              int destleft, int desttop)
{
    int i, j;
    /* approximated using putch/stdio - only used when a console exists */
    if (clite_have_console()) {
        int w = right - left + 1;
        int h = bottom - top + 1;
        char *buf = (char *)malloc((size_t)w * h + 1);
        if (!buf) return;
        for (j = 0; j < h; j++) {
            for (i = 0; i < w; i++) {
                /* read screen is not implemented - fill with spaces */
                buf[j * w + i] = ' ';
            }
            buf[j * w + w] = '\0';
        }
        for (j = 0; j < h; j++) {
            gotoxy(destleft, desttop + j);
            cputs(buf + j * w);
        }
        free(buf);
    }
}

/* ------------------------------------------------------------------ */
/*  text output                                                        */
/* ------------------------------------------------------------------ */

int putch(int ch)
{
    HANDLE h = clite_std_out();
    if (h) {
        DWORD written;
        CHAR c = (CHAR)ch;
        WriteConsoleA(h, &c, 1, &written, NULL);
    } else {
        putchar(ch);
    }
    return ch;
}

void cputs(const char *str)
{
    if (!str) return;
    if (clite_have_console()) {
        HANDLE h = clite_std_out();
        DWORD written;
        if (h)
            WriteConsoleA(h, str, (DWORD)strlen(str), &written, NULL);
        else
            fputs(str, stdout);
    } else {
        fputs(str, stdout);
    }
}

int cprintf(const char *fmt, ...)
{
    char buf[4096];
    va_list ap;
    int n;
    va_start(ap, fmt);
    n = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (n < 0) return 0;
    cputs(buf);
    return n;
}

int cscanf(const char *fmt, ...)
{
    va_list ap;
    int n;
    va_start(ap, fmt);
    n = vscanf(fmt, ap);
    va_end(ap);
    return n;
}

/* ------------------------------------------------------------------ */
/*  attributes                                                         */
/* ------------------------------------------------------------------ */

void textcolor(int color)
{
    HANDLE h = clite_std_out();
    g_text_fg = color & 0x0F;
    g_text_hi = (color & BLINK) ? 0 : 0;
    if (h)
        SetConsoleTextAttribute(h, clite_attr());
}

void textbackground(int color)
{
    HANDLE h = clite_std_out();
    g_text_bg = color & 0x07;
    if (h)
        SetConsoleTextAttribute(h, clite_attr());
}

void textattr(int attr)
{
    HANDLE h = clite_std_out();
    g_text_fg = attr & 0x0F;
    g_text_bg = (attr >> 4) & 0x07;
    g_text_hi = (attr & 0x08) ? 1 : 0;
    if (h)
        SetConsoleTextAttribute(h, clite_attr());
}

void highvideo(void)
{
    HANDLE h = clite_std_out();
    g_text_hi = 1;
    if (h)
        SetConsoleTextAttribute(h, clite_attr());
}

void lowvideo(void)
{
    HANDLE h = clite_std_out();
    g_text_hi = 0;
    if (h)
        SetConsoleTextAttribute(h, clite_attr());
}

void normvideo(void)
{
    HANDLE h = clite_std_out();
    g_text_fg = 7;
    g_text_bg = 0;
    g_text_hi = 0;
    if (h)
        SetConsoleTextAttribute(h, clite_attr());
}

/* ------------------------------------------------------------------ */
/*  timers / sound                                                     */
/* ------------------------------------------------------------------ */

void delay(unsigned int milliseconds)
{
    Sleep(milliseconds);
}

void sound(unsigned int frequency)
{
    /* continuous tone is not reproduced; play a short beep */
    (void)frequency;
    Beep(frequency > 0 ? frequency : 800, 1);
}

void nosound(void)
{
}