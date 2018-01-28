#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "utils.c"
#include "sort/binary_search.c"
#include "sort/bubble_sort.c"
#include "sort/quick_sort.c"
#include "leetcode/easy_strings_string_to_integer.c"
#include "leetcode/easy_array_remove_duplicates_from_sorted_array.c"

void test_print_arr(){
    int a[] = {1, 2, 3, 4, 5};
    print_arr(a, 5);
}

int main() {
    test_remove_duplicates_from_sorted_array();
    return 0;
}

