#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "../utils.c"

// 自己写的简单版本，下面附上 wiki 上考虑比较全的版本
int binary_search(const int *a, int len, int key) {
    if (a == NULL) {
        return -1;
    }

    int low = 0;
    int high = len - 1;

    while (low <= high) {
        int mid = (low + high) / 2;
        if (key == a[mid]) {
           return mid;
        }
        if (key < a[mid]) {
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    return -1;
}

int binary_search_from_wiki(const int* arr, int start, int end, int key) {
    if (arr == NULL) {
        return -1;
    }

    int mid = 0; // mid 在循环外 define, 这样就不需要每次在 for 内 define
    while (start <= end) {
        mid = start + (end - start) / 2; // 不使用 (start + end) / 2 是为了防止溢出

        if (key < arr[mid]) {
            end = mid - 1;
        } else if (key > arr[mid]) {
            start = mid + 1;
        } else {
            return mid; // 相等的情况放到最后判断，因为这种情况最少见
        }
    }
    return -1;
}

int binary_search_from_wiki_with_recursive(const int* arr, int start, int end, int key) {
    if (arr == NULL || start > end) {
        return -1;
    }

    int mid = start + (end - start) / 2;
    if (key > arr[mid]) {
        return binary_search_from_wiki_with_recursive(arr, mid + 1, end, key);
    } else if (key < arr[mid]) {
        return binary_search_from_wiki_with_recursive(arr, start, mid - 1, key);
    } else {
        return mid;
    }

}

void test_binary_search() {
    const int arr[] = {2,4,6,8,10,12,14,16,18,20};
    int len = sizeof(arr) / sizeof(int);

    const int test_keys[] = {0, 2, 3, 20, 30};
    const int test_excepted[] = {-1, 0, -1, len - 1, -1};
    for (int i = 0; i < ARR_SIZE(test_keys); i++) {

        int find_pos = binary_search(arr, len, test_keys[i]);
        assert(find_pos == test_excepted[i]);
    }
}

void test_binary_search_from_wiki() {
    const int arr[] = {2,4,6,8,10,12,14,16,18,20};
    int len = sizeof(arr) / sizeof(int);

    const int test_keys[] = {0, 2, 3, 20, 30};
    const int test_excepted[] = {-1, 0, -1, len - 1, -1};
    for (int i = 0; i < ARR_SIZE(test_keys); i++) {

        int find_pos = binary_search_from_wiki(arr, 0, len - 1, test_keys[i]);
        assert(find_pos == test_excepted[i]);
    }
}

void test_binary_search_from_wiki_with_recursive() {
    const int arr[] = {2,4,6,8,10,12,14,16,18,20};
    int len = sizeof(arr) / sizeof(int);

    const int test_keys[] = {0, 2, 3, 20, 30};
    const int test_excepted[] = {-1, 0, -1, len - 1, -1};
    for (int i = 0; i < ARR_SIZE(test_keys); i++) {

        int find_pos = binary_search_from_wiki_with_recursive(arr, 0, len - 1, test_keys[i]);
        assert(find_pos == test_excepted[i]);
    }

}
