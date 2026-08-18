#include <graphics.h>
#include <conio.h>
#include <stdio.h>
#include <stdlib.h>

int main()
{
    int gd = DETECT, gm;
    int x1, y1, x2, y2;
    int dx, dy, sx, sy, err, e2;

    initgraph(&gd, &gm, "");

    printf("Bresenham Line Drawing Algorithm\n");
    printf("Enter x1 y1 x2 y2: ");
    scanf("%d %d %d %d", &x1, &y1, &x2, &y2);

    dx = abs(x2 - x1);
    dy = abs(y2 - y1);
    sx = (x1 < x2) ? 1 : -1;
    sy = (y1 < y2) ? 1 : -1;
    err = dx - dy;

    while (1) {
        putpixel(x1, y1, GREEN);
        if (x1 == x2 && y1 == y2)
            break;
        e2 = 2 * err;
        if (e2 > -dy) {
            err -= dy;
            x1 += sx;
        }
        if (e2 < dx) {
            err += dx;
            y1 += sy;
        }
        delay(2);
    }

    outtextxy(10, 10, "Bresenham Line (press any key)");
    getch();
    closegraph();
    return 0;
}