#include <graphics.h>
#include <conio.h>

int main()
{
    int gd = DETECT, gm;
    int x = 100, y = 100, r = 20;
    int dx = 4, dy = 3;

    initgraph(&gd, &gm, "");

    outtextxy(180, 440, "Animation - press any key to stop");

    while (!kbhit()) {
        cleardevice();
        setcolor(YELLOW);
        circle(x, y, r);
        setfillstyle(SOLID_FILL, YELLOW);
        floodfill(x, y, YELLOW);

        x += dx;
        y += dy;
        if (x + r > getmaxx() || x - r < 0)
            dx = -dx;
        if (y + r > getmaxy() || y - r < 0)
            dy = -dy;
        delay(16);
    }

    getch();
    closegraph();
    return 0;
}