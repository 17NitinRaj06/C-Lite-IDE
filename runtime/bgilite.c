/*
 *  bgilite.c - C-Lite BGI graphics runtime.
 *
 *  Implements the Turbo C BGI graphics functions declared in
 *  include/graphics.h using native Windows GDI.  Graphics are drawn to
 *  an in-memory bitmap (double buffering) and blitted to a dedicated
 *  top-level window that is independent of the IDE.
 *
 *  The historic driver path passed to initgraph() (for example
 *  "C:\\TURBOC3\\BGI") is ignored - no BGI files are required.
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "graphics.h"

/* ------------------------------------------------------------------ */
/*  internal state                                                     */
/* ------------------------------------------------------------------ */

static HWND     g_hwnd = NULL;
static HDC      g_memdc = NULL;
static HBITMAP  g_bmp = NULL;
static int      g_w = 640;
static int      g_h = 480;
static int      g_win_w = 640;
static int      g_win_h = 480;
static int      g_initialized = 0;
static HANDLE   g_thread = NULL;

static int      g_driver = VGA;
static int      g_gmode = VGAHI;

static int      g_color = WHITE;
static int      g_bkcolor = BLACK;
static int      g_fillpat = SOLID_FILL;
static int      g_fillcolor = WHITE;
static int      g_line_style = SOLID_LINE;
static unsigned g_line_pattern = 0;
static int      g_line_width = NORM_WIDTH;

static int      g_cp_x = 0;
static int      g_cp_y = 0;

static int      g_vp_x1 = 0, g_vp_y1 = 0;
static int      g_vp_x2 = 639, g_vp_y2 = 479;
static int      g_vp_clip = 0;

static int      g_font = DEFAULT_FONT;
static int      g_dir = HORIZ_DIR;
static int      g_charsize = 1;
static int      g_just_h = LEFT_TEXT;
static int      g_just_v = TOP_TEXT;

static int      g_error = grOk;

/* classic VGA 16 color palette */
static const COLORREF g_pal[16] = {
    RGB(0, 0, 0),        /* BLACK        */
    RGB(0, 0, 170),      /* BLUE         */
    RGB(0, 170, 0),      /* GREEN        */
    RGB(0, 170, 170),    /* CYAN         */
    RGB(170, 0, 0),      /* RED          */
    RGB(170, 0, 170),    /* MAGENTA      */
    RGB(170, 85, 0),     /* BROWN        */
    RGB(170, 170, 170),  /* LIGHTGRAY    */
    RGB(85, 85, 85),     /* DARKGRAY     */
    RGB(85, 85, 255),    /* LIGHTBLUE    */
    RGB(85, 255, 85),    /* LIGHTGREEN   */
    RGB(85, 255, 255),   /* LIGHTCYAN    */
    RGB(255, 85, 85),    /* LIGHTRED     */
    RGB(255, 85, 255),   /* LIGHTMAGENTA */
    RGB(255, 255, 85),   /* YELLOW       */
    RGB(255, 255, 255)   /* WHITE        */
};

static COLORREF clite_color(int c)
{
    int r, g, b;
    if (c >= 0 && c < 16)
        return g_pal[c];
    /* colours above 15 use a bright hue wheel */
    {
        int hue = ((c * 47) % 360 + 360) % 360;
        double h = hue * 6.0 / 360.0;
        int i = (int)h;
        double f = h - i;
        unsigned char q = (unsigned char)(255 * (1.0 - f));
        unsigned char t = (unsigned char)(255 * f);
        r = g = b = 255;
        switch (i % 6) {
        case 0: r = 255; g = t; b = 0; break;
        case 1: r = q; g = 255; b = 0; break;
        case 2: r = 0; g = 255; b = t; break;
        case 3: r = 0; g = q; b = 255; break;
        case 4: r = t; g = 0; b = 255; break;
        default:r = 255; g = 0; b = q; break;
        }
    }
    return RGB(r, g, b);
}

/* map a GDI RGB value back to the nearest BGI colour index */
static int clite_bgi_index(COLORREF c)
{
    int best = 0;
    long bestd = 0x7fffffff;
    int i;
    for (i = 0; i < 16; i++) {
        long dr = (long)GetRValue(c) - (long)GetRValue(g_pal[i]);
        long dg = (long)GetGValue(c) - (long)GetGValue(g_pal[i]);
        long db = (long)GetBValue(c) - (long)GetBValue(g_pal[i]);
        long d = dr * dr + dg * dg + db * db;
        if (d < bestd) { bestd = d; best = i; }
    }
    return best;
}

/* viewport translation */
static int clite_dx(int x) { return x + g_vp_x1; }
static int clite_dy(int y) { return y + g_vp_y1; }

static void clite_refresh(void)
{
    if (g_hwnd)
        InvalidateRect(g_hwnd, NULL, FALSE);
}

static HBRUSH clite_fill_brush(void)
{
    COLORREF c = clite_color(g_fillcolor);
    switch (g_fillpat) {
    case EMPTY_FILL:
        return (HBRUSH)GetStockObject(NULL_BRUSH);
    case LINE_FILL:
        return CreateHatchBrush(HS_HORIZONTAL, c);
    case LTSLASH_FILL:
    case SLASH_FILL:
        return CreateHatchBrush(HS_BDIAGONAL, c);
    case BKSLASH_FILL:
    case LTBKSLASH_FILL:
        return CreateHatchBrush(HS_FDIAGONAL, c);
    case HATCH_FILL:
        return CreateHatchBrush(HS_CROSS, c);
    case XHATCH_FILL:
    case INTERLEAVE_FILL:
        return CreateHatchBrush(HS_DIAGCROSS, c);
    case SOLID_FILL:
    default:
        return CreateSolidBrush(c);
    }
}

static HPEN clite_pen(void)
{
    DWORD style = PS_SOLID;
    switch (g_line_style) {
    case DOTTED_LINE:  style = PS_DOT;     break;
    case CENTER_LINE:  style = PS_DASHDOT; break;
    case DASHED_LINE:  style = PS_DASH;    break;
    default:           style = PS_SOLID;   break;
    }
    return CreatePen(style, g_line_width >= THICK_WIDTH ? 3 : 1,
                     clite_color(g_color));
}

/* ------------------------------------------------------------------ */
/*  window / message loop thread                                       */
/* ------------------------------------------------------------------ */

static LRESULT CALLBACK clite_wndproc(HWND hwnd, UINT msg, WPARAM w, LPARAM l)
{
    switch (msg) {
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);
        if (g_memdc) {
            RECT rc;
            GetClientRect(hwnd, &rc);
            int cw = rc.right - rc.left;
            int ch = rc.bottom - rc.top;
            StretchBlt(hdc, 0, 0, cw, ch, g_memdc, 0, 0, g_w, g_h, SRCCOPY);
        }
        EndPaint(hwnd, &ps);
        return 0;
    }
    case WM_ERASEBKGND:
        return 1;
    case WM_SIZE: {
        RECT rc;
        GetClientRect(hwnd, &rc);
        g_win_w = rc.right - rc.left;
        g_win_h = rc.bottom - rc.top;
        return 0;
    }
    case WM_CLOSE:
        DestroyWindow(hwnd);
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    default:
        return DefWindowProcA(hwnd, msg, w, l);
    }
}

static DWORD WINAPI clite_gfx_thread(LPVOID arg)
{
    HANDLE ready = (HANDLE)arg;
    WNDCLASSA wc;
    RECT r;
    HWND hwnd;
    HDC sdc;
    MSG dummy;

    memset(&wc, 0, sizeof(wc));
    wc.lpfnWndProc = clite_wndproc;
    wc.hInstance = GetModuleHandle(NULL);
    wc.lpszClassName = "CliteBGIWindow";
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
    RegisterClassA(&wc);

    /* Establish this thread's message queue before creating the window;
       helps avoid stalls during the very first window creation. */
    PeekMessageA(&dummy, NULL, 0, 0, PM_NOREMOVE);

    r.left = 0; r.top = 0; r.right = g_w; r.bottom = g_h;
    AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);

    hwnd = CreateWindowExA(0, "CliteBGIWindow", "C-Lite Graphics Window",
                           WS_OVERLAPPEDWINDOW,
                           CW_USEDEFAULT, CW_USEDEFAULT,
                           r.right - r.left, r.bottom - r.top,
                           NULL, NULL, wc.hInstance, NULL);
    if (!hwnd) {
        g_error = grNoInitGraph;
        SetEvent(ready);
        return 0;
    }

    g_hwnd = hwnd;
    sdc = GetDC(hwnd);
    g_memdc = CreateCompatibleDC(sdc);
    g_bmp = CreateCompatibleBitmap(sdc, g_w, g_h);
    ReleaseDC(hwnd, sdc);
    if (!g_memdc || !g_bmp) {
        g_error = grNoLoadMem;
        SetEvent(ready);
        return 0;
    }
    SelectObject(g_memdc, g_bmp);
    SetBkColor(g_memdc, clite_color(g_bkcolor));
    FillRect(g_memdc, &(RECT){0, 0, g_w, g_h},
             (HBRUSH)GetStockObject(BLACK_BRUSH));
    SetEvent(ready);

    ShowWindow(hwnd, SW_SHOW);
    UpdateWindow(hwnd);

    {
        MSG msg;
        while (GetMessageA(&msg, NULL, 0, 0) > 0) {
            TranslateMessage(&msg);
            DispatchMessageA(&msg);
        }
    }
    g_hwnd = NULL;
    return 0;
}

static void clite_create_window(void)
{
    HANDLE ready = CreateEvent(NULL, TRUE, FALSE, NULL);
    g_thread = CreateThread(NULL, 0, clite_gfx_thread, ready, 0, NULL);
    if (g_thread) {
        DWORD t0 = GetTickCount();
        MSG m;
        /* Pump messages while the window thread creates the window.  The
           window manager can synchronously block window creation waiting
           for this (first) thread to process a message; if we never pump
           that wait deadlocks for several seconds. */
        for (;;) {
            if (WaitForSingleObject(ready, 50) == WAIT_OBJECT_0)
                break;
            while (PeekMessageA(&m, NULL, 0, 0, PM_REMOVE)) {
                TranslateMessage(&m);
                DispatchMessageA(&m);
            }
            if (GetTickCount() - t0 > 10000)
                break;
        }
    }
    CloseHandle(ready);
}

/* ------------------------------------------------------------------ */
/*  device / mode functions                                            */
/* ------------------------------------------------------------------ */

void initgraph(int *gdriver, int *gmode, char *pathtodriver)
{
    int driver, mode;
    int w = 640, h = 480;
    (void)pathtodriver; /* historical BGI path is ignored */

    if (!gdriver || !gmode) {
        g_error = grNotDetected;
        return;
    }
    if (g_initialized) {
        *gdriver = g_driver;
        *gmode = g_gmode;
        return;
    }

    driver = *gdriver;
    mode = *gmode;

    if (driver == DETECT) {
        driver = VGA;
        mode = VGAHI;
    }

    switch (driver) {
    case VGA:
        if (mode == VGALO)      { w = 640; h = 200; }
        else if (mode == VGAMED){ w = 640; h = 350; }
        else                    { mode = VGAHI; w = 640; h = 480; }
        break;
    case EGA:
    case EGA64:
        if (mode == EGALO) { w = 640; h = 200; }
        else               { mode = EGAHI; w = 640; h = 350; }
        break;
    case CGA:
    case MCGA:
    case ATT400:
        w = 640; h = 200;
        break;
    default:
        driver = VGA; mode = VGAHI; w = 640; h = 480;
        break;
    }

    g_driver = driver;
    g_gmode = mode;
    *gdriver = driver;
    *gmode = mode;

    g_color = WHITE;
    g_bkcolor = BLACK;
    g_fillpat = SOLID_FILL;
    g_fillcolor = WHITE;
    g_line_style = SOLID_LINE;
    g_line_pattern = 0;
    g_line_width = NORM_WIDTH;
    g_vp_x1 = 0; g_vp_y1 = 0;
    g_vp_x2 = w - 1; g_vp_y2 = h - 1;
    g_vp_clip = 0;
    g_font = DEFAULT_FONT;
    g_dir = HORIZ_DIR;
    g_charsize = 1;
    g_just_h = LEFT_TEXT;
    g_just_v = TOP_TEXT;
    g_cp_x = 0;
    g_cp_y = 0;
    g_error = grOk;

    g_w = w;
    g_h = h;
    g_win_w = w;
    g_win_h = h;
    clite_create_window();
    g_initialized = 1;
    cleardevice();
}

void closegraph(void)
{
    if (!g_initialized)
        return;
    g_initialized = 0;

    if (g_hwnd)
        PostMessageA(g_hwnd, WM_CLOSE, 0, 0);
    if (g_thread) {
        WaitForSingleObject(g_thread, 5000);
        CloseHandle(g_thread);
        g_thread = NULL;
    }
    if (g_memdc) { DeleteDC(g_memdc); g_memdc = NULL; }
    if (g_bmp)   { DeleteObject(g_bmp); g_bmp = NULL; }
    g_hwnd = NULL;
    g_win_w = 0;
    g_win_h = 0;
}

void detectgraph(int *gdriver, int *gmode)
{
    if (gdriver) *gdriver = VGA;
    if (gmode)   *gmode = VGAHI;
}

void graphdefaults(void)
{
    if (!g_initialized) return;
    g_color = WHITE;
    g_bkcolor = BLACK;
    g_fillpat = SOLID_FILL;
    g_fillcolor = WHITE;
    g_line_style = SOLID_LINE;
    g_line_pattern = 0;
    g_line_width = NORM_WIDTH;
    g_vp_x1 = 0; g_vp_y1 = 0;
    g_vp_x2 = g_w - 1; g_vp_y2 = g_h - 1;
    g_vp_clip = 0;
    g_font = DEFAULT_FONT;
    g_dir = HORIZ_DIR;
    g_charsize = 1;
    g_just_h = LEFT_TEXT;
    g_just_v = TOP_TEXT;
    g_cp_x = 0; g_cp_y = 0;
    g_error = grOk;
}

void setactivepage(int page) { (void)page; }
void setvisualpage(int page) { (void)page; }
void setallpalette(struct palettetype *palette) { (void)palette; }
void setpalette(int colornum, int color)
{
    (void)colornum; (void)color;
}
void setrgbpalette(int colornum, int red, int green, int blue)
{
    (void)colornum; (void)red; (void)green; (void)blue;
}
void getpalette(struct palettetype *palette)
{
    int i;
    if (!palette) return;
    palette->size = 16;
    for (i = 0; i < 16; i++)
        palette->colors[i] = (signed char)i;
}
int getpalettesize(void) { return 16; }
void getdefaultpalette(struct palettetype *palette)
{
    getpalette(palette);
}
const char *getdrivername(void)
{
    if (g_driver == VGA) return "VGA";
    return "C-Lite BGI";
}
char *getmodename(int mode_number)
{
    static char buf[32];
    sprintf(buf, "Mode %d", mode_number);
    return buf;
}
void getmoderange(int graphdriver, int *lomode, int *himode)
{
    if (graphdriver == VGA) { if (lomode) *lomode = VGALO; if (himode) *himode = VGAHI; }
    else                    { if (lomode) *lomode = 0;     if (himode) *himode = 0; }
}
const char *getfillpattern(void) { return NULL; }
void setfillpattern(const char *upattern, int color)
{
    (void)upattern;
    g_fillpat = USER_FILL;
    g_fillcolor = color;
}

/* ------------------------------------------------------------------ */
/*  drawing primitives                                                 */
/* ------------------------------------------------------------------ */

void putpixel(int x, int y, int color)
{
    if (!g_initialized || !g_memdc) return;
    SetPixelV(g_memdc, clite_dx(x), clite_dy(y), clite_color(color));
    clite_refresh();
}

int getpixel(int x, int y)
{
    if (!g_initialized || !g_memdc) return -1;
    return clite_bgi_index(GetPixel(g_memdc, clite_dx(x), clite_dy(y)));
}

void line(int x1, int y1, int x2, int y2)
{
    HGDIOBJ op, ob;
    HPEN pen;
    if (!g_initialized || !g_memdc) return;
    pen = clite_pen();
    op = SelectObject(g_memdc, pen);
    ob = SelectObject(g_memdc, (HGDIOBJ)GetStockObject(NULL_BRUSH));
    MoveToEx(g_memdc, clite_dx(x1), clite_dy(y1), NULL);
    LineTo(g_memdc, clite_dx(x2), clite_dy(y2));
    SetPixelV(g_memdc, clite_dx(x2), clite_dy(y2), clite_color(g_color));
    SelectObject(g_memdc, op);
    SelectObject(g_memdc, ob);
    DeleteObject(pen);
    clite_refresh();
}

void moveto(int x, int y) { g_cp_x = x; g_cp_y = y; }
void moverel(int dx, int dy) { g_cp_x += dx; g_cp_y += dy; }
void lineto(int x, int y) { line(g_cp_x, g_cp_y, x, y); g_cp_x = x; g_cp_y = y; }
void linerel(int dx, int dy) { lineto(g_cp_x + dx, g_cp_y + dy); }

void rectangle(int left, int top, int right, int bottom)
{
    HGDIOBJ op, ob;
    HPEN pen;
    if (!g_initialized || !g_memdc) return;
    pen = clite_pen();
    op = SelectObject(g_memdc, pen);
    ob = SelectObject(g_memdc, (HGDIOBJ)GetStockObject(NULL_BRUSH));
    Rectangle(g_memdc, clite_dx(left), clite_dy(top),
              clite_dx(right) + 1, clite_dy(bottom) + 1);
    SelectObject(g_memdc, op);
    SelectObject(g_memdc, ob);
    DeleteObject(pen);
    clite_refresh();
}

void bar(int left, int top, int right, int bottom)
{
    RECT r;
    HBRUSH br;
    if (!g_initialized || !g_memdc) return;
    r.left = clite_dx(left);
    r.top = clite_dy(top);
    r.right = clite_dx(right) + 1;
    r.bottom = clite_dy(bottom) + 1;
    br = clite_fill_brush();
    SetBkMode(g_memdc, OPAQUE);
    SetBkColor(g_memdc, clite_color(g_bkcolor));
    FillRect(g_memdc, &r, br);
    if (br != GetStockObject(NULL_BRUSH))
        DeleteObject(br);
    clite_refresh();
}

void bar3d(int left, int top, int right, int bottom, int depth, int topflag)
{
    int x1, y1, x2, y2;
    bar(left, top, right, bottom);
    x1 = left + depth; y1 = top - depth;
    x2 = right + depth; y2 = top - depth;
    line(x1, y1, x2, y2);
    if (topflag)
        line(left, top, x1, y1);
    line(x1, y1, x1, bottom);
    line(x2, y2, x2, bottom);
}

void circle(int x, int y, int radius)
{
    HGDIOBJ op, ob;
    HPEN pen;
    if (!g_initialized || !g_memdc) return;
    pen = clite_pen();
    op = SelectObject(g_memdc, pen);
    ob = SelectObject(g_memdc, (HGDIOBJ)GetStockObject(NULL_BRUSH));
    Ellipse(g_memdc, clite_dx(x - radius), clite_dy(y - radius),
            clite_dx(x + radius) + 1, clite_dy(y + radius) + 1);
    SelectObject(g_memdc, op);
    SelectObject(g_memdc, ob);
    DeleteObject(pen);
    clite_refresh();
}

/* sample points on an arc; angles in degrees, ccw from 3 o'clock */
static int clite_arc_points(int x, int y, int st, int en,
                            int rx, int ry, POINT *pts, int maxpts)
{
    int sweep, n, i;
    if (en <= st)
        en = st + 360;
    sweep = en - st;
    if (sweep > 360) sweep = 360;
    n = sweep + 1;
    if (n > maxpts) n = maxpts;
    for (i = 0; i < n; i++) {
        double a = (st + i) * 3.14159265358979323846 / 180.0;
        pts[i].x = clite_dx((int)(x + rx * cos(a)));
        pts[i].y = clite_dy((int)(y + ry * sin(a)));
    }
    return n;
}

void arc(int x, int y, int stangle, int endangle, int radius)
{
    POINT pts[400];
    HGDIOBJ op, ob;
    HPEN pen;
    int n;
    if (!g_initialized || !g_memdc) return;
    n = clite_arc_points(x, y, stangle, endangle, radius, radius, pts, 400);
    pen = clite_pen();
    op = SelectObject(g_memdc, pen);
    ob = SelectObject(g_memdc, (HGDIOBJ)GetStockObject(NULL_BRUSH));
    Polyline(g_memdc, pts, n);
    SelectObject(g_memdc, op);
    SelectObject(g_memdc, ob);
    DeleteObject(pen);
    clite_refresh();
}

void ellipse(int x, int y, int stangle, int endangle, int xradius, int yradius)
{
    POINT pts[400];
    HGDIOBJ op, ob;
    HPEN pen;
    int n;
    if (!g_initialized || !g_memdc) return;
    if (endangle <= stangle || (endangle - stangle) >= 360) {
        /* full ellipse */
        pen = clite_pen();
        op = SelectObject(g_memdc, pen);
        ob = SelectObject(g_memdc, (HGDIOBJ)GetStockObject(NULL_BRUSH));
        Ellipse(g_memdc, clite_dx(x - xradius), clite_dy(y - yradius),
                clite_dx(x + xradius) + 1, clite_dy(y + yradius) + 1);
        SelectObject(g_memdc, op);
        SelectObject(g_memdc, ob);
        DeleteObject(pen);
        clite_refresh();
        return;
    }
    n = clite_arc_points(x, y, stangle, endangle, xradius, yradius, pts, 400);
    pen = clite_pen();
    op = SelectObject(g_memdc, pen);
    ob = SelectObject(g_memdc, (HGDIOBJ)GetStockObject(NULL_BRUSH));
    Polyline(g_memdc, pts, n);
    SelectObject(g_memdc, op);
    SelectObject(g_memdc, ob);
    DeleteObject(pen);
    clite_refresh();
}

static void clite_polygon(int numpoints, int *polypoints, int fill)
{
    POINT *pts;
    HGDIOBJ op, ob;
    HPEN pen;
    HBRUSH br;
    int i;
    if (!g_initialized || !g_memdc || numpoints < 2 || !polypoints) return;
    pts = (POINT *)malloc(sizeof(POINT) * numpoints);
    if (!pts) return;
    for (i = 0; i < numpoints; i++) {
        pts[i].x = clite_dx(polypoints[i * 2]);
        pts[i].y = clite_dy(polypoints[i * 2 + 1]);
    }
    pen = clite_pen();
    op = SelectObject(g_memdc, pen);
    if (fill) {
        br = clite_fill_brush();
        SetBkMode(g_memdc, OPAQUE);
        SetBkColor(g_memdc, clite_color(g_bkcolor));
    } else {
        br = (HBRUSH)GetStockObject(NULL_BRUSH);
    }
    ob = SelectObject(g_memdc, br);
    if (fill)
        Polygon(g_memdc, pts, numpoints);
    else
        Polyline(g_memdc, pts, numpoints);
    SelectObject(g_memdc, op);
    SelectObject(g_memdc, ob);
    if (br != GetStockObject(NULL_BRUSH))
        DeleteObject(br);
    DeleteObject(pen);
    free(pts);
    clite_refresh();
}

void drawpoly(int numpoints, int *polypoints)
{
    clite_polygon(numpoints, polypoints, 0);
}

void fillpoly(int numpoints, int *polypoints)
{
    clite_polygon(numpoints, polypoints, 1);
}

static void clite_pie(int x, int y, int st, int en, int rx, int ry)
{
    POINT pts[400];
    POINT *poly;
    HGDIOBJ op, ob;
    HPEN pen;
    HBRUSH br;
    int n, i;
    if (!g_initialized || !g_memdc) return;
    n = clite_arc_points(x, y, st, en, rx, ry, pts, 400);
    poly = (POINT *)malloc(sizeof(POINT) * (n + 2));
    if (!poly) return;
    poly[0].x = clite_dx(x);
    poly[0].y = clite_dy(y);
    for (i = 0; i < n; i++)
        poly[i + 1] = pts[i];
    poly[n + 1] = poly[0];
    pen = clite_pen();
    op = SelectObject(g_memdc, pen);
    br = clite_fill_brush();
    SetBkMode(g_memdc, OPAQUE);
    SetBkColor(g_memdc, clite_color(g_bkcolor));
    ob = SelectObject(g_memdc, br);
    Polygon(g_memdc, poly, n + 2);
    SelectObject(g_memdc, op);
    SelectObject(g_memdc, ob);
    if (br != GetStockObject(NULL_BRUSH))
        DeleteObject(br);
    DeleteObject(pen);
    free(poly);
    clite_refresh();
}

void pieslice(int x, int y, int stangle, int endangle, int radius)
{
    clite_pie(x, y, stangle, endangle, radius, radius);
}

void sector(int x, int y, int stangle, int endangle,
            int xradius, int yradius)
{
    clite_pie(x, y, stangle, endangle, xradius, yradius);
}

void floodfill(int x, int y, int border)
{
    HGDIOBJ ob;
    HBRUSH br;
    if (!g_initialized || !g_memdc) return;
    br = clite_fill_brush();
    ob = SelectObject(g_memdc, br);
    ExtFloodFill(g_memdc, clite_dx(x), clite_dy(y),
                 clite_color(border), FLOODFILLBORDER);
    SelectObject(g_memdc, ob);
    if (br != GetStockObject(NULL_BRUSH))
        DeleteObject(br);
    clite_refresh();
}

/* ------------------------------------------------------------------ */
/*  region / image functions                                           */
/* ------------------------------------------------------------------ */

unsigned imagesize(int left, int top, int right, int bottom)
{
    int w = right - left + 1;
    int h = bottom - top + 1;
    if (w <= 0 || h <= 0) return 0;
    return (unsigned)(w * h + 8);
}

void getimage(int left, int top, int right, int bottom, void *bitmap)
{
    unsigned char *b = (unsigned char *)bitmap;
    unsigned char *p;
    int w = right - left + 1, h = bottom - top + 1;
    int x, y;
    if (!bitmap) return;
    b[0] = (unsigned char)(w & 255);
    b[1] = (unsigned char)((w >> 8) & 255);
    b[2] = (unsigned char)(h & 255);
    b[3] = (unsigned char)((h >> 8) & 255);
    p = b + 4;
    for (y = top; y <= bottom; y++)
        for (x = left; x <= right; x++)
            *p++ = (unsigned char)getpixel(x, y);
}

void putimage(int left, int top, void *bitmap, int op)
{
    unsigned char *b = (unsigned char *)bitmap;
    unsigned char *p;
    int w, h, x, y;
    if (!bitmap) return;
    w = b[0] | (b[1] << 8);
    h = b[2] | (b[3] << 8);
    p = b + 4;
    for (y = top; y < top + h; y++)
        for (x = left; x < left + w; x++) {
            int c = *p++;
            int existing = getpixel(x, y);
            int nc = c;
            switch (op) {
            case XOR_PUT: nc = c ^ existing; break;
            case OR_PUT:  nc = c | existing; break;
            case AND_PUT: nc = c & existing; break;
            case NOT_PUT: nc = (~c) & 0xFF; break;
            default: break;
            }
            putpixel(x, y, nc);
        }
    clite_refresh();
}

/* ------------------------------------------------------------------ */
/*  attributes / state                                                 */
/* ------------------------------------------------------------------ */

void setcolor(int color) { g_color = color; }
int  getcolor(void) { return g_color; }

void setbkcolor(int color)
{
    g_bkcolor = color;
    if (g_memdc)
        SetBkColor(g_memdc, clite_color(color));
}

int getbkcolor(void) { return g_bkcolor; }

void cleardevice(void)
{
    HBRUSH br;
    if (!g_initialized || !g_memdc) return;
    br = CreateSolidBrush(clite_color(g_bkcolor));
    FillRect(g_memdc, &(RECT){0, 0, g_w, g_h}, br);
    DeleteObject(br);
    g_cp_x = 0;
    g_cp_y = 0;
    clite_refresh();
}

void clearviewport(void)
{
    HBRUSH br;
    if (!g_initialized || !g_memdc) return;
    br = CreateSolidBrush(clite_color(g_bkcolor));
    FillRect(g_memdc, &(RECT){g_vp_x1, g_vp_y1,
                              g_vp_x2 + 1, g_vp_y2 + 1}, br);
    DeleteObject(br);
    g_cp_x = 0;
    g_cp_y = 0;
    clite_refresh();
}

void setlinestyle(int linestyle, unsigned upattern, int thickness)
{
    g_line_style = linestyle;
    g_line_pattern = upattern;
    g_line_width = thickness;
}

void getlinesettings(struct linesettingstype *lineinfo)
{
    if (!lineinfo) return;
    lineinfo->linestyle = g_line_style;
    lineinfo->upattern = g_line_pattern;
    lineinfo->thickness = g_line_width;
}

void setfillstyle(int pattern, int color)
{
    if (pattern < EMPTY_FILL || pattern > USER_FILL)
        pattern = SOLID_FILL;
    g_fillpat = pattern;
    g_fillcolor = color;
}

void getfillsettings(struct fillsettingstype *fillinfo)
{
    if (!fillinfo) return;
    fillinfo->pattern = g_fillpat;
    fillinfo->color = g_fillcolor;
}

void setviewport(int left, int top, int right, int bottom, int clip)
{
    g_vp_x1 = left;
    g_vp_y1 = top;
    g_vp_x2 = right;
    g_vp_y2 = bottom;
    g_vp_clip = clip;
    if (g_memdc) {
        if (clip) {
            HRGN rgn = CreateRectRgn(left, top, right + 1, bottom + 1);
            SelectClipRgn(g_memdc, rgn);
            DeleteObject(rgn);
        } else {
            SelectClipRgn(g_memdc, NULL);
        }
    }
}

void getviewsettings(struct viewporttype *viewport)
{
    if (!viewport) return;
    viewport->left = g_vp_x1;
    viewport->top = g_vp_y1;
    viewport->right = g_vp_x2;
    viewport->bottom = g_vp_y2;
    viewport->clip = g_vp_clip;
}

/* ------------------------------------------------------------------ */
/*  text functions                                                     */
/* ------------------------------------------------------------------ */

static HFONT clite_build_font(void)
{
    int height = 16 * (g_charsize > 0 ? g_charsize : 1);
    int esc = (g_dir == VERT_DIR) ? 900 : 0;
    DWORD italic = 0;
    const char *face = "Fixedsys";
    switch (g_font) {
    case TRIPLEX_FONT:     face = "Times New Roman"; italic = TRUE; break;
    case SMALL_FONT:       face = "MS Sans Serif"; break;
    case SANS_SERIF_FONT:  face = "Arial"; break;
    case GOTHIC_FONT:      face = "Impact"; break;
    case SCRIPT_FONT:      face = "Comic Sans MS"; break;
    case SIMPLEX_FONT:     face = "Arial"; break;
    case COMPLEX_FONT:     face = "Times New Roman"; break;
    default:               face = "Fixedsys"; break;
    }
    return CreateFontA(height, 0, esc, esc, FW_NORMAL, italic, 0, 0,
                       ANSI_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                       DEFAULT_QUALITY, FIXED_PITCH, face);
}

static void clite_draw_text(int x, int y, const char *s)
{
    HFONT f;
    HGDIOBJ of;
    SIZE sz;
    UINT align = 0;
    int len;
    if (!s) return;
    len = (int)strlen(s);
    f = clite_build_font();
    of = SelectObject(g_memdc, f);
    SetBkMode(g_memdc, TRANSPARENT);
    SetTextColor(g_memdc, clite_color(g_color));
    switch (g_just_h) {
    case CENTER_TEXT: align |= TA_CENTER; break;
    case RIGHT_TEXT:  align |= TA_RIGHT; break;
    default:          align |= TA_LEFT; break;
    }
    switch (g_just_v) {
    case CENTER_TEXT: align |= TA_CENTER; break;
    case BOTTOM_TEXT: align |= TA_BOTTOM; break;
    default:          align |= TA_TOP; break;
    }
    SetTextAlign(g_memdc, align);
    GetTextExtentPoint32A(g_memdc, s, len, &sz);
    TextOutA(g_memdc, clite_dx(x), clite_dy(y), s, len);
    SelectObject(g_memdc, of);
    DeleteObject(f);
    (void)sz;
}

void outtext(const char *textstring)
{
    SIZE sz;
    HFONT f;
    HGDIOBJ of;
    if (!g_initialized || !g_memdc || !textstring) return;
    clite_draw_text(g_cp_x, g_cp_y, textstring);
    f = clite_build_font();
    of = SelectObject(g_memdc, f);
    GetTextExtentPoint32A(g_memdc, textstring,
                          (int)strlen(textstring), &sz);
    SelectObject(g_memdc, of);
    DeleteObject(f);
    if (g_dir == VERT_DIR)
        g_cp_y += sz.cy;
    else
        g_cp_x += sz.cx;
    clite_refresh();
}

void outtextxy(int x, int y, const char *textstring)
{
    if (!g_initialized || !g_memdc || !textstring) return;
    clite_draw_text(x, y, textstring);
    clite_refresh();
}

void settextstyle(int font, int direction, int charsize)
{
    if (font < DEFAULT_FONT || font > BOLD_FONT)
        font = DEFAULT_FONT;
    if (direction != VERT_DIR)
        direction = HORIZ_DIR;
    g_font = font;
    g_dir = direction;
    g_charsize = charsize;
}

void settextjustify(int horiz, int vert)
{
    if (horiz == LEFT_TEXT || horiz == CENTER_TEXT || horiz == RIGHT_TEXT)
        g_just_h = horiz;
    if (vert == BOTTOM_TEXT || vert == CENTER_TEXT || vert == TOP_TEXT)
        g_just_v = vert;
}

void gettextsettings(struct textsettingstype *texttypeinfo)
{
    if (!texttypeinfo) return;
    texttypeinfo->font = g_font;
    texttypeinfo->direction = g_dir;
    texttypeinfo->charsize = g_charsize;
    texttypeinfo->horiz = g_just_h;
    texttypeinfo->vert = g_just_v;
}

int textheight(const char *textstring)
{
    HFONT f;
    HGDIOBJ of;
    SIZE sz;
    if (!g_memdc) return 16;
    f = clite_build_font();
    of = SelectObject(g_memdc, f);
    GetTextExtentPoint32A(g_memdc, textstring ? textstring : "",
                          textstring ? (int)strlen(textstring) : 0, &sz);
    SelectObject(g_memdc, of);
    DeleteObject(f);
    return sz.cy;
}

int textwidth(const char *textstring)
{
    HFONT f;
    HGDIOBJ of;
    SIZE sz;
    if (!g_memdc) return 8;
    f = clite_build_font();
    of = SelectObject(g_memdc, f);
    GetTextExtentPoint32A(g_memdc, textstring ? textstring : "",
                          textstring ? (int)strlen(textstring) : 0, &sz);
    SelectObject(g_memdc, of);
    DeleteObject(f);
    return sz.cx;
}

/* ------------------------------------------------------------------ */
/*  query functions                                                    */
/* ------------------------------------------------------------------ */

int getx(void) { return g_cp_x; }
int gety(void) { return g_cp_y; }
int getmaxx(void) { return g_w - 1; }
int getmaxy(void) { return g_h - 1; }
int getmaxcolor(void) { return 15; }

void getarccoords(struct arccoordstype *arccoords)
{
    if (!arccoords) return;
    arccoords->x = 0;
    arccoords->y = 0;
    arccoords->xstart = 0;
    arccoords->ystart = 0;
    arccoords->xend = 0;
    arccoords->yend = 0;
}

int graphresult(void)
{
    int e = g_error;
    g_error = grOk;
    return e;
}

char *grapherrormsg(int errorcode)
{
    static char buf[64];
    switch (errorcode) {
    case grOk:             return "No error";
    case grNoInitGraph:    return "Graphics not initialized";
    case grNotDetected:    return "Graphics hardware not detected";
    case grFileNotFound:   return "Device driver file not found";
    case grInvalidDriver:  return "Invalid device driver";
    case grNoLoadMem:      return "Not enough memory to load driver";
    case grNoScanMem:      return "Out of memory in scan fill";
    case grNoFloodMem:     return "Out of memory in flood fill";
    case grFontNotFound:   return "Font file not found";
    case grNoFontMem:      return "Not enough memory for font";
    case grInvalidMode:    return "Invalid graphics mode";
    case grError:          return "Graphics error";
    case grIOerror:        return "Graphics I/O error";
    case grInvalidFont:    return "Invalid font file";
    case grInvalidFontNum: return "Invalid font number";
    case grInvalidDeviceNum: return "Invalid device number";
    default:
        sprintf(buf, "Graphics error %d", errorcode);
        return buf;
    }
}

int clite_graphics_ready(void)
{
    return g_initialized && g_hwnd != NULL;
}