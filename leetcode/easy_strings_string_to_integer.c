#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "../utils.c"

bool is_space(char c) {
    if (c == 0x20) {
        return true;
    }
    if (c > 0x9 && c < 0xd) {
        return true;
    }
    return false;
}
int atoi_from_python_source_code(char* str) {
    if (str == NULL) {
        return 0;
    }
    char* s = str;

    while (s != '\0' && is_space(*s)) {
        s++;
    }

    int sign = 1;
    switch (*s) {
        case '-':
            sign = -1;
        case '+':
            s++;
    }

    long long result = 0;
    int dis = -1;
    while (*s != '\0' && !is_space(*s)) {
        dis = *s - '0';
        if (dis < 0 || dis > 9) {
            return 0;
        }
        result = result * 10 + dis;
        s++;
    }

    while (*s != '\0' && is_space(*s)) {
        s++;
    }

    if (*s != '\0' || dis == -1) {
        return 0;
    }
    return result * sign;
}


void test_atoi_from_python_source_code() {
    char* test_cases[] = {
            "",
            "1",
            " 123",
            " -123",
            " 123 ",
            " 123a",
            " a ",
    };
    const int test_result[] = {0, 1, 123, -123, 123, 0, 0};
    int len = ARR_SIZE(test_cases);
    for (int i = 0; i < len; i++) {
        int result = atoi_from_python_source_code(test_cases[i]);
        assert(result == test_result[i]);
    }
}
