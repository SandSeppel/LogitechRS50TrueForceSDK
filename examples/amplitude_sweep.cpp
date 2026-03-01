/**
 * examples/amplitude_sweep.cpp
 * ============================
 * Interactive amplitude step comparison at 83 Hz.
 *
 * Build & run:
 *   cmake --build build && sudo ./build/amplitude_sweep
 */

#include <trueforce/wheel.hpp>
#include <cstdio>
#include <vector>
#include <string>

static constexpr float FREQ = 83.0f;

int main() {
    struct Step { float amp; const char* label; };
    std::vector<Step> steps = {
        {0.001f, "0.1%   — barely perceptible"},
        {0.003f, "0.3%"},
        {0.005f, "0.5%   — PCAP reference: real BeamNG engine rumble"},
        {0.010f, "1%"},
        {0.025f, "2.5%"},
        {0.050f, "5%"},
        {0.100f, "10%"},
        {0.250f, "25%"},
        {0.500f, "50%"},
        {1.000f, "100%   — full scale"},
    };

    trueforce::TrueForceWheel wheel;
    wheel.init();
    std::printf("\nFrequency: %.0f Hz.  Press Enter to advance, Ctrl+C to quit.\n\n", FREQ);

    for (auto& s : steps) {
        int counts = static_cast<int>(s.amp * 0x7FFF);
        std::printf("  amp=%.3f  (%d counts)  %s\n", s.amp, counts, s.label);
        wheel.vibrate(FREQ, s.amp, 3.0);
        wheel.stop();
        std::printf("  → next: ");
        std::getchar();
    }
}
