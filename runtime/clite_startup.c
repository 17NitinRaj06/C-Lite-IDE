/*
 *  clite_startup.c - C-Lite runtime startup.
 *
 *  Runs before main() to make standard output unbuffered so that text
 *  produced by console programs appears immediately in the C-Lite IDE
 *  terminal (important for interactive printf/scanf programs).
 */
#include <stdio.h>

#if defined(_WIN32)
#include <windows.h>
#endif

#if defined(__GNUC__)
__attribute__((constructor))
static void clite_runtime_startup(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
}
#endif