#include <graphics.h>
#include <conio.h>
#include <stdio.h>

int main()
{
    int gd = DETECT, gm;
    int square[] = {200, 200, 300, 200, 300, 300, 200, 300};
    int sh, i;

    initgraph(&gd, &gm, "");

    printf("2D Shearing (x-shear)\n");
    printf("Enter shear factor: ");
    scanf("%d", &sh);

    setcolor(RED);
    drawpoly(4, square);

    for (i = 0; i < 8; i += 2)
        square[i] = square[i] + sh * square[i + 1];

    setcolor(GREEN);
    drawpoly(4, square);

    outtextxy(30, 30, "Shearing: red = original, green = sheared");
    getch();
    closegraph();
    return 0;
}