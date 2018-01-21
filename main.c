#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "utils.c"
#include "sort/binary_search.c"

void test_print_arr(){
    int a[] = {1, 2, 3, 4, 5};
    print_arr(a, 5);
}

int main() {
    test_binary_search_from_wiki();
    return 0;
}

