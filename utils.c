#ifndef _UTILS_
#define _UTILS_

#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>


#define ARR_SIZE(arr) (sizeof(arr) / sizeof(arr[0]))

void print_arr(int *a, int len) {
    printf("[ ");
    for (int i = 0; i < len; i++) {
        printf("%d ", i);
    }
    printf("]\n");
}

#endif