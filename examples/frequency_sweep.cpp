/**
 * examples/frequency_sweep.cpp
 * ============================
 * Two passes: full amplitude then realistic amplitude.
 *
 * Build & run:
 *   cmake --build build && sudo ./build/frequency_sweep
 */

#include <trueforce/wheel.hpp>
#include <cstdio>

int main() {
    trueforce::TrueForceWheel wheel;
    wheel.init();

    std::printf("\n=== Pass 1: full amplitude (1.0) ===\n");
    wheel.freq_sweep(10.0f, 1000.0f, 1.0f, 10.0);
}
