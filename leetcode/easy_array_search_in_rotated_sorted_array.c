#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../utils.c"

int search_in_rotated_sorted_array(int* arr, int len, int key) {
    if (arr == NULL || len <= 0) {
        return -1;
    }
    int start = 0;
    int end = len - 1;
    while (start <= end) {
        int mid = start + (end - start) / 2;
        if (arr[mid] == key) {
            return mid;
        }
        if (arr[mid] <= arr[end]) {
            if (key > arr[mid] && key <= arr[end]) {
                start = mid + 1;
            } else {
                end = mid - 1;
            }
        } else {
            if (key < arr[mid] && arr[start] <= key) {
                end = mid - 1;
            } else {
                start = mid + 1;
            }
        }
    }
    return -1;
}

void test_search_in_rotated_sorted_array() {
    int test_arrs[][6] = {
            {1, 2, 3, 4, 5, 6},
            {5, 6, 0, 1, 2, 3},
            {3, 4, 5, 6, 0, 1},
    };
    int test_cases[] = {2, 6, 1};
    int excepted_cases[][3] = { // test_arrs_index, find_key, excepted_result
        {0, 2, 1},
        {1, 6, 1},
        {2, 1, 5},
        {1, 7, -1}
    };
    int len = ARR_SIZE(excepted_cases);
    for (int i = 0; i < len; i++) {
        int* excepted_case = excepted_cases[i];
        int result =  search_in_rotated_sorted_array(test_arrs[excepted_case[0]], 6, excepted_case[1]);
        assert(result == excepted_case[2]);
    }
}

