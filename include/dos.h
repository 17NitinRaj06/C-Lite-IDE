/*
 *  dos.h - minimal Turbo C dos.h compatibility header for C-Lite IDE.
 *
 *  Only the functions commonly used in college programs are provided.
 *  Hardware interrupt functions (int86 etc.) cannot run on modern
 *  Windows and are provided as safe stubs.
 */
#ifndef CLITE_DOS_H
#define CLITE_DOS_H

#ifdef __cplusplus
extern "C" {
#endif

void delay(unsigned int milliseconds);
void sleep(unsigned int seconds);
void sound(unsigned int frequency);
void nosound(void);

union REGS {
    struct { unsigned int ax, bx, cx, dx, si, di, cflag, flags; } x;
    struct { unsigned char al, ah, bl, bh, cl, ch, dl, dh; } h;
};

struct SREGS {
    unsigned int es;
    unsigned int cs;
    unsigned int ss;
    unsigned int ds;
};

struct date {
    int da_year;
    char da_day;
    char da_mon;
};

struct time {
    unsigned char ti_hour;
    unsigned char ti_min;
    unsigned char ti_sec;
    unsigned char ti_hund;
};

void getdate(struct date *datep);
void setdate(struct date *datep);
void gettime(struct time *timep);
void settime(struct time *timep);

int int86(int intno, union REGS *inregs, union REGS *outregs);
int int86x(int intno, union REGS *inregs, union REGS *outregs,
           struct SREGS *sregs);
int intdos(union REGS *inregs, union REGS *outregs);

#ifdef __cplusplus
}
#endif

#endif /* CLITE_DOS_H */
