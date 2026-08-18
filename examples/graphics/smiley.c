#include <graphics.h>
#include <conio.h>

int main()
{
    int gd = DETECT, gm;

    initgraph(&gd, &gm, "");

    /* face */
    setcolor(YELLOW);
    circle(320, 240, 150);
    setfillstyle(SOLID_FILL, YELLOW);
    floodfill(320, 240, YELLOW);

    /* eyes */
    setcolor(BLACK);
    circle(270, 200, 15);
    circle(370, 200, 15);
    setfillstyle(SOLID_FILL, BLACK);
    floodfill(270, 200, BLACK);
    floodfill(370, 200, BLACK);

    /* smile */
    setcolor(BLACK);
    arc(320, 260, 200, 340, 80);

    /* nose */
    line(320, 220, 310, 250);
    line(320, 220, 330, 250);
    line(310, 250, 330, 250);

    getch();
    closegraph();
    return 0;
}