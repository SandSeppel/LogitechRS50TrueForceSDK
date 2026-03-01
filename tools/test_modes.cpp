/**
 * tools/test_modes.cpp
 * ====================
 * Diagnostic test modes — all implemented via the TrueForce SDK.
 *
 * Usage:  sudo ./build/test_modes [mode]
 *
 * Modes
 * -----
 *   engine     83 Hz sine: 3 s at 100%, then PCAP reference (0.5%)
 *   ampsweep   Step through 0.1%–100% amplitude at 83 Hz (interactive)
 *   sweep      Frequency sweep 10 → 500 Hz at full amplitude
 *   bump       Decaying impulses every 500 ms at 150 Hz
 *   freq       Slow frequency sweep 20 → 500 Hz at 30%
 *   silence    Send neutral packets for 3 seconds
 *   scan       Isolate individual buffer pairs (protocol debug)
 *   bisect     Find which setup command causes wheel rotation
 */

#include <trueforce/wheel.hpp>
#include <trueforce/protocol.hpp>
#include <trueforce/device.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>
#include <tuple>
#include <vector>

using namespace trueforce;
using namespace std::chrono;
using namespace std::chrono_literals;

// ── Individual test modes ──────────────────────────────────────────

static void mode_engine(TrueForceWheel& wheel) {
    wheel.stream([](float t) {
        float amp = (t < 3.0f) ? 1.0f : 0.005f;
        return std::make_tuple(0.0f, amp, 83.0f);
    }, 8.0, TF_GAIN_DEFAULT, "engine: 3s@100% then PCAP reference (0.5%)");
}

static void mode_sweep(TrueForceWheel& wheel) {
    wheel.freq_sweep(10.0f, 500.0f, 1.0f, 10.0);
}

static void mode_bump(TrueForceWheel& wheel) {
    wheel.bump(150.0f, 20.0f, 0.5f, 6.0);
}

static void mode_ampsweep(TrueForceWheel& wheel) {
    struct Step { float amp; const char* label; };
    std::vector<Step> steps = {
        {0.001f, "0.1%"},
        {0.003f, "0.3%"},
        {0.005f, "0.5% — PCAP reference"},
        {0.010f, "1%"},
        {0.050f, "5%"},
        {0.100f, "10%"},
        {0.250f, "25%"},
        {0.500f, "50%"},
        {1.000f, "100% full scale"},
    };
    std::printf("\n=== Amplitude sweep @ 83 Hz ===\n");
    for (auto& s : steps) {
        std::printf("\n  %s  (%d counts)\n", s.label, (int)(s.amp * 0x7FFF));
        wheel.vibrate(83.0f, s.amp, 3.0);
        wheel.stop();
        std::printf("  Enter=next, Ctrl+C=quit: ");
        if (std::getchar() == EOF) break;
    }
}

static void mode_freq(TrueForceWheel& wheel) {
    wheel.freq_sweep(20.0f, 500.0f, 0.30f, 15.0);
}

static void mode_silence(TrueForceWheel& wheel) {
    wheel.stream([](float) { return std::make_tuple(0.0f, 0.0f, 0.0f); },
                 3.0, TF_GAIN_DEFAULT, "silence");
}

// ── Scan: isolate individual buffer pairs ──────────────────────────

static void mode_scan(Device& dev) {
    std::printf("\n=== SCAN: individual pairs in the 13-pair buffer ===\n\n");

    const auto interval = duration_cast<nanoseconds>(
        duration<double>{1.0 / UPDATE_HZ});

    uint8_t reg        = 0;
    int     sample_idx = PAIRS_PER_PKT - 1;

    for (int target = -1; target < PAIRS_PER_PKT; ++target) {
        if (target == -1)
            std::printf("  Enter → ALL 13 pairs: ");
        else
            std::printf("  Enter → Pair %d (bytes %d-%d): ",
                        target, 12 + target*4, 15 + target*4);
        std::fflush(stdout);
        if (std::getchar() == EOF) break;

        auto t_start = steady_clock::now();
        auto t_next  = t_start;
        int sent = 0;

        while (steady_clock::now() - t_start < 2s) {
            if (steady_clock::now() < t_next)
                std::this_thread::sleep_until(t_next);
            t_next += interval;

            Packet pkt{};
            pkt[0] = 0x01; pkt[4] = 0x01; pkt[5] = reg;
            pkt[6] = 0x00; pkt[7] = 0x80;
            pkt[8] = 0x00; pkt[9] = 0x80;
            pkt[10] = static_cast<uint8_t>(SHIFT_PER_PKT);
            pkt[11] = TF_GAIN_DEFAULT;

            // Fill all pairs with neutral
            for (int j = 0; j < PAIRS_PER_PKT; ++j) {
                pkt[12 + j*4    ] = 0x00; pkt[12 + j*4 + 1] = 0x80;
                pkt[12 + j*4 + 2] = 0x00; pkt[12 + j*4 + 3] = 0x80;
            }

            // Activate target pair(s)
            auto write_pair = [&](int j, float t_s) {
                int raw = static_cast<int>(
                    0x8000 + 0x7FFF * std::sin(2.0 * M_PI * 83.0 * t_s));
                uint16_t val = static_cast<uint16_t>(
                    std::clamp(raw, 0, 0xFFFF));
                pkt[12 + j*4    ] = val & 0xFF;
                pkt[12 + j*4 + 1] = (val >> 8) & 0xFF;
                pkt[12 + j*4 + 2] = val & 0xFF;
                pkt[12 + j*4 + 3] = (val >> 8) & 0xFF;
            };

            if (target == -1) {
                for (int j = 0; j < PAIRS_PER_PKT; ++j) {
                    float t_s = (sample_idx - 12 + j) / static_cast<float>(SAMPLE_RATE);
                    write_pair(j, t_s);
                }
            } else {
                float t_s = sample_idx / static_cast<float>(SAMPLE_RATE);
                write_pair(target, t_s);
            }

            send(dev, pkt, 10);
            recv(dev, 1);
            reg = (reg + 1) & 0xFF;
            sample_idx += SHIFT_PER_PKT;
            ++sent;
        }
        std::printf("  %d packets sent\n", sent);
    }
}

// ── Bisect: find the setup command that causes rotation ────────────

static void mode_bisect(Device& dev) {
    std::printf("\n=== BISECT: find setup command that causes rotation ===\n\n");

    const auto interval = duration_cast<nanoseconds>(
        duration<double>{1.0 / UPDATE_HZ});

    uint8_t reg        = 0;
    int     sample_idx = PAIRS_PER_PKT - 1;

    auto neutral_loop = [&](double seconds, const char* label) {
        std::printf("  [%s] %.0fs...", label, seconds);
        std::fflush(stdout);
        auto t_end  = steady_clock::now() + duration_cast<steady_clock::duration>(
                          duration<double>{seconds});
        auto t_next = steady_clock::now();
        while (steady_clock::now() < t_end) {
            if (steady_clock::now() < t_next)
                std::this_thread::sleep_until(t_next);
            t_next += interval;
            auto pkt = build_packet(reg, 0.0f, 1.0f, 83.0f, sample_idx);
            send(dev, pkt, 10);
            recv(dev, 1);
            reg = (reg + 1) & 0xFF;
            sample_idx += SHIFT_PER_PKT;
        }
        std::printf(" done\n");
    };

    neutral_loop(3.0, "baseline");

    for (int i = 0; i < (int)SETUP_CMDS.size(); ++i) {
        const auto& pkt = SETUP_CMDS[i];
        std::printf("\n  Sending CMD=0x%02x slot=0x%02x...\n", pkt[4], pkt[5]);
        send(dev, pkt, 100);
        std::this_thread::sleep_for(3ms);

        char lbl[32];
        std::snprintf(lbl, sizeof(lbl), "after CMD[%d] 0x%02x", i, pkt[4]);
        neutral_loop(3.0, lbl);

        std::printf("  Rotating after CMD[%d]? (y/n/q): ", i);
        std::fflush(stdout);
        char ans = static_cast<char>(std::getchar());
        std::getchar(); // consume newline

        if (ans == 'q') break;
        if (ans == 'y') {
            std::printf("  *** CULPRIT: CMD[%d] = 0x%02x slot=0x%02x ***\n",
                        i, pkt[4], pkt[5]);
            break;
        }
    }
}

// ── Dispatch ───────────────────────────────────────────────────────

static void print_usage() {
    std::printf(
        "Usage: sudo ./test_modes [mode]\n\n"
        "Modes:\n"
        "  engine     83 Hz: 3s full then PCAP reference\n"
        "  ampsweep   amplitude steps 0.1%%–100%% @ 83 Hz (interactive)\n"
        "  sweep      frequency sweep 10→500 Hz\n"
        "  bump       decaying impulses @ 150 Hz\n"
        "  freq       freq sweep 20→500 Hz @ 30%%\n"
        "  silence    neutral output for 3 s\n"
        "  scan       isolate buffer pairs (debug)\n"
        "  bisect     find rotation-causing setup command\n"
    );
}

int main(int argc, char* argv[]) {
    std::string mode = (argc > 1) ? argv[1] : "engine";

    // Modes that use the high-level wheel API
    if (mode == "engine" || mode == "ampsweep" || mode == "sweep" ||
        mode == "bump"   || mode == "freq"     || mode == "silence")
    {
        TrueForceWheel wheel;
        wheel.init();

        if      (mode == "engine")   mode_engine(wheel);
        else if (mode == "ampsweep") mode_ampsweep(wheel);
        else if (mode == "sweep")    mode_sweep(wheel);
        else if (mode == "bump")     mode_bump(wheel);
        else if (mode == "freq")     mode_freq(wheel);
        else if (mode == "silence")  mode_silence(wheel);
    }
    // Modes that need raw device access
    else if (mode == "scan" || mode == "bisect") {
        Device dev = open_device();
        send_init(dev, /*skip_setup=*/mode == "scan");
        if (mode == "scan")   mode_scan(dev);
        else                  mode_bisect(dev);
    }
    else {
        print_usage();
        return 1;
    }

    return 0;
}
