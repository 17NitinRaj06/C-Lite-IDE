#include <graphics.h>
#include <conio.h>

int main()
{
    int gd = DETECT, gm;

    int hex[] = {320, 80, 460, 160, 460, 300,
                 320, 380, 180, 300, 180, 160};

    initgraph(&gd, &gm, "");

    /* outline */
    setcolor(WHITE);
    drawpoly(6, hex);

    /* fill with different patterns, one wedge at a time */
    setfillstyle(HATCH_FILL, LIGHTBLUE);
    floodfill(320, 240, WHITE);

    setfillstyle(SLASH_FILL, GREEN);
    floodfill(250, 160, WHITE);

    setfillstyle(BKSLASH_FILL, MAGENTA);
    floodfill(390, 160, WHITE);

    setfillstyle(LINE_FILL, LIGHTRED);
    floodfill(250, 300, WHITE);

    setfillstyle(XHATCH_FILL, YELLOW);
    floodfill(390, 300, WHITE);

    outtextxy(240, 410, "Polygon Filling with floodfill + patterns");
    getch();
    closegraph();
    return 0;
}