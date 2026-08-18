/*
 *  conio.h - Turbo C conio compatibility header for C-Lite IDE.
 *
 *  Provides console input/output functions used by classic Turbo C
 *  programs. When the program runs inside the C-Lite IDE terminal the
 *  functions fall back to stdio-based behaviour; when the program is
 *  run from a real Windows console the native console functions are
 *  used so that clrscr(), gotoxy(), textcolor(), getch() etc. work as
 *  they did in Turbo C.
 */
#ifndef CLITE_CONIO_H
#define CLITE_CONIO_H

#include <stdarg.h>

#ifdef __cplusplus
extern "C" {
#endif

#define BLINK 128

/* screen / cursor control */
void clrscr(void);
void clreol(void);
void gotoxy(int x, int y);
void insline(void);
void delline(void);
void textmode(int mode);
void window(int left, int top, int right, int bottom);
int  wherex(void);
int  wherey(void);
void movetext(int left, int top, int right, int bottom,
              int destleft, int desttop);

/* character input */
int  getch(void);
int  getche(void);
int  kbhit(void);
int  putch(int ch);

/* text output */
void cputs(const char *str);
int  cprintf(const char *fmt, ...);
int  cscanf(const char *fmt, ...);

/* attribute control */
void textcolor(int color);
void textbackground(int color);
void textattr(int attr);
void highvideo(void);
void lowvideo(void);
void normvideo(void);

/* timers / sound (kept here for Turbo C compatibility; also in dos.h) */
void delay(unsigned int milliseconds);
void sound(unsigned int frequency);
void nosound(void);

#ifdef __cplusplus
}
#endif

#endif /* CLITE_CONIO_H */
