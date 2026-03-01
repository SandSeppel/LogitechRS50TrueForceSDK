/**
 * examples/road_texture.cpp
 * =========================
 * Simulates different road surfaces back-to-back:
 *   smooth tarmac, rough tarmac, cobblestone, gravel, rumble strip
 *
 * Build & run:
 *   cmake --build build && sudo ./build/road_texture
 */

#include <trueforce/wheel.hpp>
#include <cmath>
#include <cstdio>
#include <tuple>
#include <vector>
#include <functional>
#include <string>

using Gen = std::function<std::tuple<float,float,float>(float)>;

static Gen smooth_tarmac() {
    return [](float) { return std::make_tuple(0.0f, 0.002f, 80.0f); };
}

static Gen rough_tarmac() {
    return [](float) { return std::make_tuple(0.0f, 0.006f, 95.0f); };
}

static Gen cobblestone() {
    return [](float t) {
        float base = std::sin(2.0f * M_PI * 8.0f * t);
        float amp  = 0.04f * std::max(0.0f, base);
        return std::make_tuple(0.0f, amp, 120.0f);
    };
}

static Gen gravel() {
    return [](float t) {
        float a = std::sin(2.0f * M_PI * 75.0f  * t) * 0.5f;
        float b = std::sin(2.0f * M_PI * 130.0f * t) * 0.5f;
        float amp = std::abs(a + b) * 0.05f;
        return std::make_tuple(0.0f, amp, 100.0f);
    };
}

static Gen rumble_strip() {
    return [](float t) {
        float phase = std::fmod(t, 0.2f) / 0.2f;
        float amp   = (phase < 0.4f) ? 0.12f : 0.0f;
        return std::make_tuple(0.0f, amp, 85.0f);
    };
}

int main() {
    struct Surface { Gen gen; double dur; const char* name; };
    std::vector<Surface> surfaces = {
        { smooth_tarmac(), 3.0, "smooth tarmac"  },
        { rough_tarmac(),  3.0, "rough tarmac"   },
        { cobblestone(),   3.0, "cobblestone"     },
        { gravel(),        3.0, "gravel"          },
        { rumble_strip(),  3.0, "rumble strip"    },
    };

    trueforce::TrueForceWheel wheel;
    wheel.init();

    for (auto& s : surfaces) {
        std::printf("\n  Surface: %s\n", s.name);
        wheel.stream(s.gen, s.dur);
        wheel.stop();
    }
}
