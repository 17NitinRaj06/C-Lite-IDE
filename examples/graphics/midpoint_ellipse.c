#include <graphics.h>
#include <conio.h>
#include <stdio.h>

int main()
{
    int gd = DETECT, gm;
    int xc, yc, rx, ry;
    float x, y, d1, d2;

    initgraph(&gd, &gm, "");

    printf("Midpoint Ellipse Algorithm\n");
    printf("Enter center (xc yc): ");
    scanf("%d %d", &xc, &yc);
    printf("Enter radii (rx ry): ");
    scanf("%d %d", &rx, &ry);

    x = 0;
    y = ry;
    d1 = (ry * ry) - (rx * rx * ry) + (0.25 * rx * rx);

    while ((ry * ry * x) < (rx * rx * y)) {
        putpixel((int)(xc + x), (int)(yc + y), CYAN);
        putpixel((int)(xc - x), (int)(yc + y), CYAN);
        putpixel((int)(xc + x), (int)(yc - y), CYAN);
        putpixel((int)(xc - x), (int)(yc - y), CYAN);
        x++;
        if (d1 < 0) {
            d1 += 2 * ry * ry * x + ry * ry;
        } else {
            y--;
            d1 += 2 * ry * ry * x - 2 * rx * rx * y + ry * ry;
        }
        delay(2);
    }

    d2 = ry * ry * (x + 0.5) * (x + 0.5)
         + rx * rx * (y - 1) * (y - 1)
         - rx * rx * ry * ry;

    while (y >= 0) {
        putpixel((int)(xc + x), (int)(yc + y), CYAN);
        putpixel((int)(xc - x), (int)(yc + y), CYAN);
        putpixel((int)(xc + x), (int)(yc - y), CYAN);
        putpixel((int)(xc - x), (int)(yc - y), CYAN);
        y--;
        if (d2 > 0) {
            d2 -= 2 * rx * rx * y + rx * rx;
        } else {
            x++;
            d2 += 2 * ry * ry * x - 2 * rx * rx * y + rx * rx;
        }
        delay(2);
    }

    outtextxy(xc - 60, yc + ry + 20, "Midpoint Ellipse");
    getch();
    closegraph();
    return 0;
}