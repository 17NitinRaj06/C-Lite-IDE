#include <graphics.h>
#include <conio.h>

int main()
{
    int gd = DETECT, gm;

    initgraph(&gd, &gm, "");

    setcolor(RED);
    arc(320, 150, 0, 180, 80);              /* arc */

    setcolor(GREEN);
    ellipse(320, 300, 0, 360, 120, 60);     /* ellipse */

    setcolor(BLUE);
    pieslice(100, 380, 30, 150, 70);        /* filled pie slice */

    setcolor(YELLOW);
    sector(560, 380, 45, 135, 80, 60);      /* filled sector */

    setlinestyle(DOTTED_LINE, 0, NORM_WIDTH);
    setcolor(LIGHTGRAY);
    line(50, 60, 590, 60);                  /* dotted line */

    setlinestyle(SOLID_LINE, 0, THICK_WIDTH);
    setcolor(WHITE);
    line(50, 80, 590, 80);                  /* thick line */

    setcolor(LIGHTCYAN);
    settextstyle(DEFAULT_FONT, HORIZ_DIR, 1);
    outtextxy(180, 450, "arc  ellipse  pieslice  sector");
    settextstyle(TRIPLEX_FONT, HORIZ_DIR, 2);
    outtextxy(180, 30, "BGI Shapes Demo");

    getch();
    closegraph();
    return 0;
}