#include <graphics.h>
#include <conio.h>
#include <stdio.h>

int main()
{
    int gd = DETECT, gm;
    int square[] = {100, 100, 200, 100, 200, 200, 100, 200};
    int tx, ty, i;

    initgraph(&gd, &gm, "");

    printf("2D Translation\n");
    printf("Enter translation (tx ty): ");
    scanf("%d %d", &tx, &ty);

    setcolor(RED);
    fillpoly(4, square);

    for (i = 0; i < 8; i += 2) {
        square[i] += tx;
        square[i + 1] += ty;
    }

    setcolor(GREEN);
    fillpoly(4, square);

    outtextxy(40, 30, "Translation: red = original, green = moved");
    getch();
    closegraph();
    return 0;
}