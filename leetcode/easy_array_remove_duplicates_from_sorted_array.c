#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

void remove_duplicates_from_sorted_array(int* arr, int len) {
    if (arr == NULL || len <= 1) {
        return;
    }
    int index = 0;
    for (int i = 1; i < len; i++) {
        if (arr[index] != arr[i]) {
            index++;
            arr[index] = arr[i];
        }
    }
}

void test_remove_duplicates_from_sorted_array() {
    int test_cases[][4] = {
            {1,1, 3, 4},
            {1,2, 3, 3},
            {1,2, 2, 4},
    };
    int expected_cases[][3] = {
            {1, 3, 4},
            {1, 2, 3},
            {1, 2, 4},
    };

    for (int i = 0; i < 3; i++) {
        int* test_case = test_cases[i];
        remove_duplicates_from_sorted_array(test_case, 4);
        int* expected_case = expected_cases[i];
        for (int j = 0; j < 3; j++) {
            assert(expected_case[j] == test_case[j]);
        }
    }
}


