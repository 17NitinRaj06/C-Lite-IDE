#include <graphics.h>
#include <conio.h>
#include <stdio.h>
#include <stdlib.h>

int main()
{
    int gd = DETECT, gm;
    int x1, y1, x2, y2, steps, i;
    float dx, dy, x, y, xin, yin;

    initgraph(&gd, &gm, "");

    printf("DDA Line Drawing Algorithm\n");
    printf("Enter starting point (x1 y1): ");
    scanf("%d %d", &x1, &y1);
    printf("Enter ending point (x2 y2): ");
    scanf("%d %d", &x2, &y2);

    dx = x2 - x1;
    dy = y2 - y1;
    steps = (abs(dx) > abs(dy)) ? abs(dx) : abs(dy);
    xin = dx / steps;
    yin = dy / steps;
    x = x1;
    y = y1;

    for (i = 0; i <= steps; i++) {
        putpixel((int)x, (int)y, LIGHTBLUE);
        x += xin;
        y += yin;
        delay(4);
    }

    outtextxy(10, 10, "DDA Line (press any key)");
    getch();
    closegraph();
    return 0;
}
// unsaved change
// unsaved change