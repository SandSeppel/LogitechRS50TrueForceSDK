/**
 * examples/custom_waveforms.cpp
 * ==============================
 * Sine, sawtooth, square, triangle, band-limited noise.
 *
 * Build & run:
 *   cmake --build build && sudo ./build/custom_waveforms
 */

#include <trueforce/wheel.hpp>
#include <cmath>
#include <cstdio>
#include <thread>
#include <chrono>
#include <functional>
#include <string>
#include <vector>

static constexpr float FREQ = 80.0f;
static constexpr float AMP  = 0.08f;
static constexpr double DUR  = 3.0;

static float sine(float t) {
    return std::sin(2.0f * M_PI * FREQ * t);
}

static float sawtooth(float t) {
    return 2.0f * std::fmod(t * FREQ, 1.0f) - 1.0f;
}

static float square(float t) {
    return std::sin(2.0f * M_PI * FREQ * t) >= 0.0f ? 1.0f : -1.0f;
}

static float triangle(float t) {
    float phase = std::fmod(t * FREQ, 1.0f);
    return (phase < 0.5f) ? 4.0f * phase - 1.0f : 3.0f - 4.0f * phase;
}

static float bandlimited_noise(float t) {
    return (std::sin(2.0f * M_PI * 73.0f  * t) * 0.4f
          + std::sin(2.0f * M_PI * 113.0f * t) * 0.3f
          + std::sin(2.0f * M_PI * 157.0f * t) * 0.2f
          + std::sin(2.0f * M_PI * 211.0f * t) * 0.1f);
}

int main() {
    struct Wave { std::function<float(float)> fn; const char* name; };
    std::vector<Wave> waves = {
        { sine,              "sine"              },
        { sawtooth,          "sawtooth"          },
        { square,            "square"            },
        { triangle,          "triangle"          },
        { bandlimited_noise, "band-limited noise"},
    };

    trueforce::TrueForceWheel wheel;
    wheel.init();

    for (auto& w : waves) {
        std::printf("\n  Waveform: %s  (%.0f Hz, amp=%.2f)\n", w.name, FREQ, AMP);
        wheel.stream_waveform(w.fn, AMP, DUR, w.name);
        wheel.stop();
        std::this_thread::sleep_for(std::chrono::milliseconds(300));
    }
}
