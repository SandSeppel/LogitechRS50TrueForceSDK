/**
 * examples/bumps.cpp
 * ==================
 * Kerb, pothole, expansion joints, single crash impact.
 *
 * Build & run:
 *   cmake --build build && sudo ./build/bumps
 */

#include <trueforce/wheel.hpp>
#include <cmath>
#include <cstdio>
#include <thread>
#include <chrono>

static void one_shot_impact(trueforce::TrueForceWheel& wheel,
                             float freq = 200.0f,
                             float amp  = 0.8f,
                             float decay = 30.0f,
                             double duration = 0.5)
{
    wheel.stream([freq, amp, decay](float t) {
        return std::make_tuple(0.0f, amp * std::exp(-t * decay), freq);
    }, duration);
}

int main() {
    trueforce::TrueForceWheel wheel;
    wheel.init();

    std::printf("\n--- Kerb strike (every 600 ms, hard) ---\n");
    wheel.bump(180.0f, 40.0f, 0.6f, 5.0);
    wheel.stop();

    std::printf("\n--- Pothole (every 1.5 s, medium) ---\n");
    wheel.bump(120.0f, 18.0f, 1.5f, 6.0);
    wheel.stop();

    std::printf("\n--- Expansion joints (every 300 ms, gentle) ---\n");
    wheel.bump(80.0f, 12.0f, 0.3f, 5.0);
    wheel.stop();

    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    std::printf("\n--- Single crash impact ---\n");
    one_shot_impact(wheel, 200.0f, 1.0f, 15.0f, 1.0);
}
