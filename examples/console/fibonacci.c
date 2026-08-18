#include <stdio.h>
#include <conio.h>

int main()
{
    int n, i;
    long a = 0, b = 1, next;

    printf("Fibonacci Series\n");
    printf("Enter number of terms: ");
    scanf("%d", &n);

    if (n <= 0) {
        printf("Please enter a positive number\n");
        getch();
        return 1;
    }

    printf("Fibonacci series: ");
    for (i = 1; i <= n; i++) {
        printf("%ld ", a);
        next = a + b;
        a = b;
        b = next;
    }
    printf("\n");

    printf("Press any key to exit...\n");
    getch();
    return 0;
}