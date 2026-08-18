#include <graphics.h>
#include <conio.h>

int main()
{
    int gd = DETECT, gm;

    initgraph(&gd, &gm, "");

    setcolor(WHITE);
    circle(320, 240, 150);
    setcolor(RED);
    circle(320, 240, 120);
    setcolor(GREEN);
    circle(320, 240, 90);
    setcolor(BLUE);
    circle(320, 240, 60);
    setcolor(YELLOW);
    circle(320, 240, 30);

    outtextxy(280, 400, "Concentric Circles (BGI circle)");
    getch();
    closegraph();
    return 0;
}
// unsaved change
