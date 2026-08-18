#include <graphics.h>
#include <conio.h>
#include <stdio.h>

int main()
{
    int gd = DETECT, gm;
    int rect[] = {150, 150, 250, 150, 250, 250, 150, 250};
    int sx, sy, i;

    initgraph(&gd, &gm, "");

    printf("2D Scaling\n");
    printf("Enter scale factors (sx sy): ");
    scanf("%d %d", &sx, &sy);

    setcolor(RED);
    drawpoly(4, rect);

    for (i = 0; i < 8; i += 2)
        rect[i] = rect[i] * sx / 2;

    for (i = 1; i < 8; i += 2)
        rect[i] = rect[i] * sy / 2;

    setcolor(GREEN);
    drawpoly(4, rect);

    outtextxy(30, 30, "Scaling: red = original, green = scaled");
    getch();
    closegraph();
    return 0;
}