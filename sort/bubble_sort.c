#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include "../utils.c"

void test_bubble_search(int* a, int len) {
    if (a == NULL || len <=1) {
        return;
    }

    for (int i = 0; i < len; i++) {
        for (int j = 1; j < len - i; j++) {
            if (a[j - i] > a[j]) {
                int tmp = a[j - i];
                a[j - i] = a[j];
                a[j] = tmp;
            }
        }
    }
}

void test_bubble_sort() {
    const int arr[] = {3, 5, 1, 2, 0};
    int len = ARR_SIZE(arr);

    test_bubble_sort(arr, len);
    const int test_result[] = {0, 1, 2, 3, 5};
    for (int i = 0; i < len; i++) {
        assert(arr[i] == test_result[i]);
    }
}
