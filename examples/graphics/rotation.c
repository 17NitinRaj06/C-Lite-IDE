#include <graphics.h>
#include <conio.h>
#include <stdio.h>
#include <math.h>

int main()
{
    int gd = DETECT, gm;
    int rect[] = {300, 150, 400, 150, 400, 250, 300, 250};
    float angle, rad;
    int cx = 350, cy = 200, i, x, y;

    initgraph(&gd, &gm, "");

    printf("2D Rotation about (%d, %d)\n", cx, cy);
    printf("Enter angle in degrees: ");
    scanf("%f", &angle);
    rad = angle * 3.14159f / 180.0f;

    setcolor(RED);
    drawpoly(4, rect);

    for (i = 0; i < 8; i += 2) {
        x = rect[i];
        y = rect[i + 1];
        rect[i] = (int)(cx + (x - cx) * cos(rad) - (y - cy) * sin(rad));
        rect[i + 1] = (int)(cy + (x - cx) * sin(rad) + (y - cy) * cos(rad));
    }

    setcolor(GREEN);
    drawpoly(4, rect);

    outtextxy(30, 30, "Rotation: red = original, green = rotated");
    getch();
    closegraph();
    return 0;
}