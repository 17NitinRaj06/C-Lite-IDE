#include <stdio.h>
#include <conio.h>

#define SIZE 5

int main()
{
    int arr[SIZE], i, sum = 0, largest;
    float average;

    printf("Array Operations (%d elements)\n", SIZE);
    for (i = 0; i < SIZE; i++) {
        printf("Enter element %d: ", i + 1);
        scanf("%d", &arr[i]);
    }

    largest = arr[0];
    for (i = 0; i < SIZE; i++) {
        sum += arr[i];
        if (arr[i] > largest)
            largest = arr[i];
    }
    average = (float)sum / SIZE;

    printf("\nArray: ");
    for (i = 0; i < SIZE; i++)
        printf("%d ", arr[i]);

    printf("\nSum     = %d\n", sum);
    printf("Average = %.2f\n", average);
    printf("Largest = %d\n", largest);

    printf("\nPress any key to exit...\n");
    getch();
    return 0;
}