#include <graphics.h>
#include <conio.h>

int main()
{
    int gd = DETECT, gm;

    int triangle[] = {100, 100, 300, 100, 200, 200};
    int hexagon[] = {350, 100, 500, 100, 560, 200,
                     500, 300, 350, 300, 290, 200};

    initgraph(&gd, &gm, "");

    setcolor(YELLOW);
    drawpoly(3, triangle);
    outtextxy(110, 90, "Triangle (drawpoly)");

    setfillstyle(SOLID_FILL, MAGENTA);
    fillpoly(6, hexagon);
    outtextxy(340, 320, "Hexagon (fillpoly)");

    getch();
    closegraph();
    return 0;
}