/*
 *  graphics.h - Turbo C BGI graphics compatibility header for C-Lite IDE.
 *
 *  This header provides the classic Borland Turbo C graphics functions
 *  and constants. The implementation is provided by the C-Lite runtime
 *  (runtime/bgilite.c) which renders using native Windows GDI.
 *
 *  Programs written for Turbo C / Turbo C++ computer-graphics courses
 *  should compile and run without modification.
 */
#ifndef CLITE_GRAPHICS_H
#define CLITE_GRAPHICS_H

#ifdef __cplusplus
extern "C" {
#endif

/* ----- graphics drivers ----- */
#define DETECT        0
#define CGA           1
#define MCGA          2
#define EGA           3
#define EGA64         4
#define EGAMONO       5
#define IBM8514       6
#define HERCMONO      7
#define ATT400        8
#define VGA           9
#define PC3270       10

/* ----- VGA graphics modes ----- */
#define VGALO         0
#define VGAMED        1
#define VGAHI         2

/* ----- CGA modes ----- */
#define CGAC0         0
#define CGAC1         1
#define CGAC2         2
#define CGAC3         3
#define CGAHI         4

/* ----- MCGA modes ----- */
#define MCGAC0        0
#define MCGAC1        1
#define MCGAC2        2
#define MCGAC3        3
#define MCGAMED       4
#define MCGAHI        5

/* ----- EGA modes ----- */
#define EGALO         0
#define EGAHI         1

#define EGAMONOHI     0

/* ----- IBM8514 modes ----- */
#define IBM8514LO     0
#define IBM8514HI     1

/* ----- HERC modes ----- */
#define HERCG         0
#define HERCCOLOR     1
#define HERCMONOHI    3

/* ----- ATT400 modes ----- */
#define ATT400C0      0
#define ATT400C1      1
#define ATT400C2      2
#define ATT400C3      3
#define ATT400MED     4
#define ATT400HI      5

#define PC3270HI      0

/* ----- colors (VGA 16-color palette) ----- */
#define BLACK          0
#define BLUE           1
#define GREEN          2
#define CYAN           3
#define RED            4
#define MAGENTA        5
#define BROWN          6
#define LIGHTGRAY      7
#define DARKGRAY       8
#define LIGHTBLUE      9
#define LIGHTGREEN    10
#define LIGHTCYAN     11
#define LIGHTRED      12
#define LIGHTMAGENTA  13
#define YELLOW        14
#define WHITE         15

/* ----- fill patterns ----- */
#define EMPTY_FILL      0
#define SOLID_FILL      1
#define LINE_FILL       2
#define LTSLASH_FILL    3
#define SLASH_FILL      4
#define BKSLASH_FILL    5
#define LTBKSLASH_FILL  6
#define HATCH_FILL      7
#define XHATCH_FILL     8
#define INTERLEAVE_FILL 9
#define WIDE_DOT_FILL  10
#define CLOSE_DOT_FILL 11
#define USER_FILL      12

/* ----- line styles ----- */
#define SOLID_LINE      0
#define DOTTED_LINE     1
#define CENTER_LINE     2
#define DASHED_LINE     3
#define USERBIT_LINE    4

/* ----- line widths ----- */
#define NORM_WIDTH      1
#define THICK_WIDTH     3

/* ----- text direction ----- */
#define HORIZ_DIR       0
#define VERT_DIR        1

/* ----- text justification ----- */
#define LEFT_TEXT       0
#define CENTER_TEXT     1
#define RIGHT_TEXT      2
#define BOTTOM_TEXT     0
#define TOP_TEXT        2
#define VCENTER_TEXT    1

/* ----- font styles ----- */
#define DEFAULT_FONT          0
#define TRIPLEX_FONT          1
#define SMALL_FONT            2
#define SANS_SERIF_FONT       3
#define GOTHIC_FONT           4
#define SCRIPT_FONT           5
#define SIMPLEX_FONT          6
#define TRIPLEX_SCR_FONT      7
#define COMPLEX_FONT          8
#define EUROPEAN_FONT         9
#define BOLD_FONT            10

/* ----- putimage operators ----- */
#define COPY_PUT        0
#define XOR_PUT         1
#define OR_PUT          2
#define AND_PUT         3
#define NOT_PUT         4

/* ----- graphresult error codes ----- */
#define grOk                0
#define grNoInitGraph      -1
#define grNotDetected      -2
#define grFileNotFound     -3
#define grInvalidDriver    -4
#define grNoLoadMem        -5
#define grNoScanMem        -6
#define grNoFloodMem       -7
#define grFontNotFound     -8
#define grNoFontMem        -9
#define grInvalidMode     -10
#define grError           -11
#define grIOerror         -12
#define grInvalidFont     -13
#define grInvalidFontNum  -14
#define grInvalidDeviceNum -15

/* ----- palette structures ----- */
struct palettetype {
    unsigned char size;
    signed char colors[256];
};

/* ----- BGI structure types ----- */
struct arccoordstype {
    int x, y, xstart, ystart, xend, yend;
};

struct fillsettingstype {
    int pattern;
    int color;
};

struct linesettingstype {
    int linestyle;
    unsigned upattern;
    int thickness;
};

struct textsettingstype {
    int font;
    int direction;
    int charsize;
    int horiz;
    int vert;
};

struct viewporttype {
    int left, top, right, bottom, clip;
};

/* ----- device / mode functions ----- */
void initgraph(int *gdriver, int *gmode, char *pathtodriver);
void closegraph(void);
void detectgraph(int *gdriver, int *gmode);
void graphdefaults(void);
void setactivepage(int page);
void setvisualpage(int page);
void setallpalette(struct palettetype *palette);
void setpalette(int colornum, int color);
void setrgbpalette(int colornum, int red, int green, int blue);
void getpalette(struct palettetype *palette);
int getpalettesize(void);
void getdefaultpalette(struct palettetype *palette);
const char *getdrivername(void);
char *getmodename(int mode_number);
void getmoderange(int graphdriver, int *lomode, int *himode);
const char *getfillpattern(void);
void setfillpattern(const char *upattern, int color);

/* ----- drawing primitives ----- */
void putpixel(int x, int y, int color);
int  getpixel(int x, int y);
void line(int x1, int y1, int x2, int y2);
void lineto(int x, int y);
void linerel(int dx, int dy);
void moveto(int x, int y);
void moverel(int dx, int dy);
void rectangle(int left, int top, int right, int bottom);
void bar(int left, int top, int right, int bottom);
void bar3d(int left, int top, int right, int bottom, int depth, int topflag);
void circle(int x, int y, int radius);
void arc(int x, int y, int stangle, int endangle, int radius);
void ellipse(int x, int y, int stangle, int endangle, int xradius, int yradius);
void fillellipse(int x, int y, int xradius, int yradius);
void drawpoly(int numpoints, int *polypoints);
void fillpoly(int numpoints, int *polypoints);
void pieslice(int x, int y, int stangle, int endangle, int radius);
void sector(int x, int y, int stangle, int endangle, int xradius, int yradius);
void floodfill(int x, int y, int border);

/* ----- region / image functions ----- */
unsigned imagesize(int left, int top, int right, int bottom);
void getimage(int left, int top, int right, int bottom, void *bitmap);
void putimage(int left, int top, void *bitmap, int op);

/* ----- attribute / state functions ----- */
void setcolor(int color);
int  getcolor(void);
void setbkcolor(int color);
int  getbkcolor(void);
void cleardevice(void);
void clearviewport(void);
void setlinestyle(int linestyle, unsigned upattern, int thickness);
void getlinesettings(struct linesettingstype *lineinfo);
void setfillstyle(int pattern, int color);
void getfillsettings(struct fillsettingstype *fillinfo);
void setviewport(int left, int top, int right, int bottom, int clip);
void getviewsettings(struct viewporttype *viewport);

/* ----- text functions ----- */
void outtext(const char *textstring);
void outtextxy(int x, int y, const char *textstring);
void settextstyle(int font, int direction, int charsize);
void settextjustify(int horiz, int vert);
void gettextsettings(struct textsettingstype *texttypeinfo);
int  textheight(const char *textstring);
int  textwidth(const char *textstring);

/* ----- query functions ----- */
int getx(void);
int gety(void);
int getmaxx(void);
int getmaxy(void);
int getmaxcolor(void);
void getarccoords(struct arccoordstype *arccoords);
int graphresult(void);
char *grapherrormsg(int errorcode);

/* ----- internal (used by runtime; not part of Turbo C) ----- */
int  clite_graphics_ready(void);

#ifdef __cplusplus
}
#endif

#endif /* CLITE_GRAPHICS_H */
