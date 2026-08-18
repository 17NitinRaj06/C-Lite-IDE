#include <graphics.h>
#include <conio.h>

int main()
{
    int gd = DETECT, gm;

    initgraph(&gd, &gm, "");

    setcolor(RED);
    rectangle(50, 50, 250, 350);
    outtextxy(120, 35, "Rectangle (outline)");

    setfillstyle(SOLID_FILL, BLUE);
    bar(280, 150, 380, 350);

    setfillstyle(LINE_FILL, GREEN);
    bar(400, 100, 500, 350);

    setfillstyle(HATCH_FILL, LIGHTRED);
    bar(520, 200, 620, 350);

    outtextxy(300, 380, "Bars with different fill styles");

    getch();
    closegraph();
    return 0;
}