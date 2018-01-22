#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>



void quick_sort(int* arr, int left, int right) {
    if (arr == NULL || right <= left) {
        return;
    }

    int start = left;
    int end = right;

    int pivot = arr[left]; // 选取数组第一个数作为轴心

    while (start < end) {
        while (start < end && arr[end] >= pivot) {
            end--;
        }

        if (start < end) {
            arr[start] = arr[end];
            start++;
        }

        while (start < end && arr[start] < pivot) {
            start++;
        }

        if (start < end) {
            arr[end] = arr[start];
            end--;
        }
    }

    arr[start] = pivot; // 设置轴心数的值
    quick_sort(arr, left, start -1);
    quick_sort(arr, start + 1, right);
}

void test_quick_sort() {
    int arr[] = {3, 7, 1, 2, 0};
    int len = ARR_SIZE(arr);

    quick_sort(arr, 0, len - 1);

    const int test_result[] = {0, 1, 2, 3, 7};
    for (int i = 0; i < len; i++) {
        assert(arr[i] == test_result[i]);
    }
}
