#include <graphics.h>
#include <conio.h>
#include <stdio.h>

#define INSIDE 0
#define LEFT 1
#define RIGHT 2
#define BOTTOM 4
#define TOP 8

#define XMIN 120
#define YMIN 120
#define XMAX 520
#define YMAX 360

int compute_code(int x, int y)
{
    int code = INSIDE;
    if (x < XMIN) code |= LEFT;
    if (x > XMAX) code |= RIGHT;
    if (y < YMIN) code |= BOTTOM;
    if (y > YMAX) code |= TOP;
    return code;
}

void clip_line(int x1, int y1, int x2, int y2)
{
    int c1 = compute_code(x1, y1);
    int c2 = compute_code(x2, y2);
    int accept = 0;

    while (1) {
        if (!(c1 | c2)) {
            accept = 1;
            break;
        } else if (c1 & c2) {
            break;
        } else {
            int code_out = c1 ? c1 : c2;
            int x = 0, y = 0;

            if (code_out & TOP) {
                x = x1 + (x2 - x1) * (YMAX - y1) / (y2 - y1);
                y = YMAX;
            } else if (code_out & BOTTOM) {
                x = x1 + (x2 - x1) * (YMIN - y1) / (y2 - y1);
                y = YMIN;
            } else if (code_out & RIGHT) {
                y = y1 + (y2 - y1) * (XMAX - x1) / (x2 - x1);
                x = XMAX;
            } else if (code_out & LEFT) {
                y = y1 + (y2 - y1) * (XMIN - x1) / (x2 - x1);
                x = XMIN;
            }

            if (code_out == c1) {
                x1 = x;
                y1 = y;
                c1 = compute_code(x1, y1);
            } else {
                x2 = x;
                y2 = y;
                c2 = compute_code(x2, y2);
            }
        }
    }

    if (accept) {
        setcolor(GREEN);
        line(x1, y1, x2, y2);
    }
}

int main()
{
    int gd = DETECT, gm;
    int x1, y1, x2, y2;

    initgraph(&gd, &gm, "");

    printf("Cohen-Sutherland Line Clipping\n");
    printf("Enter x1 y1 x2 y2: ");
    scanf("%d %d %d %d", &x1, &y1, &x2, &y2);

    setcolor(RED);
    rectangle(XMIN, YMIN, XMAX, YMAX);
    setcolor(DARKGRAY);
    line(x1, y1, x2, y2);

    clip_line(x1, y1, x2, y2);

    outtextxy(40, 40, "Red = clip window, gray = original, green = clipped");
    getch();
    closegraph();
    return 0;
}