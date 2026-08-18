#include <stdio.h>
#include <conio.h>

long factorial(int n)
{
    long fact = 1;
    int i;
    for (i = 2; i <= n; i++)
        fact *= i;
    return fact;
}

int main()
{
    int n;

    printf("Factorial Calculator\n");
    printf("Enter a positive integer: ");
    scanf("%d", &n);

    if (n < 0) {
        printf("Factorial of a negative number is undefined\n");
    } else {
        printf("%d! = %ld\n", n, factorial(n));
    }

    printf("Press any key to exit...\n");
    getch();
    return 0;
}