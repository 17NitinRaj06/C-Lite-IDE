#include <graphics.h>
#include <conio.h>

int main()
{
    int gd = DETECT, gm;
    int triangle[] = {250, 100, 400, 100, 325, 250};
    int i;

    initgraph(&gd, &gm, "");

    setcolor(RED);
    drawpoly(3, triangle);

    /* reflect across x-axis (y -> -y + maxy) */
    for (i = 0; i < 6; i += 2)
        triangle[i + 1] = getmaxy() - triangle[i + 1];

    setcolor(GREEN);
    drawpoly(3, triangle);

    outtextxy(60, 20, "Reflection: red = original, green = across x-axis");
    getch();
    closegraph();
    return 0;
}