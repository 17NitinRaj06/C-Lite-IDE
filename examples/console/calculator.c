#include <stdio.h>
#include <conio.h>

int main()
{
    float a, b, result;
    char op;

    printf("Simple Calculator\n");
    printf("Enter expression (e.g. 5 + 3): ");
    scanf("%f %c %f", &a, &op, &b);

    switch (op) {
    case '+':
        result = a + b;
        break;
    case '-':
        result = a - b;
        break;
    case '*':
        result = a * b;
        break;
    case '/':
        if (b == 0) {
            printf("Error: division by zero\n");
            getch();
            return 1;
        }
        result = a / b;
        break;
    default:
        printf("Unknown operator %c\n", op);
        getch();
        return 1;
    }

    printf("%.2f %c %.2f = %.2f\n", a, op, b, result);
    printf("Press any key to exit...\n");
    getch();
    return 0;
}