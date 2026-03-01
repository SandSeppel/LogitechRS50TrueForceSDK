/**
 * examples/engine_rumble.cpp
 * ==========================
 * Simulates engine vibration with a rising RPM curve.
 *
 *  0–5 s  : idle (800) → redline (7000)
 *  5–8 s  : holds at redline
 *  8–10 s : redline → idle
 *
 * Build & run:
 *   cmake --build build && sudo ./build/engine_rumble
 */

#include <trueforce/wheel.hpp>

static float rpm_curve(float t) {
    if (t < 5.0f)
        return 800.0f + (7000.0f - 800.0f) * (t / 5.0f);
    if (t < 8.0f)
        return 7000.0f;
    return 7000.0f - (7000.0f - 800.0f) * ((t - 8.0f) / 2.0f);
}

int main() {
    trueforce::TrueForceWheel wheel;
    wheel.init();
    // wheel.engine(
    //     rpm_curve,
    //     /*duration=*/10.0,
    //     /*rpm_min=*/0.0f,  /*rpm_max=*/7000.0f,
    //     /*freq_min=*/40.0f,  /*freq_max=*/180.0f,
    //     /*amp_min=*/0.002f,  /*amp_max=*/1.0f
    // );
    wheel.vibrate(680.0f, 0.5f, 3.0);
    return 0;
}
