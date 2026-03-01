#include "wheel.hpp"
#include <algorithm>
#include <chrono>
#include <csignal>
#include <cstdio>
#include <cmath>
#include <thread>
#include <tuple>

namespace trueforce {

using clk  = std::chrono::steady_clock;
using ns   = std::chrono::nanoseconds;
using fsec = std::chrono::duration<float>;

static const ns PACKET_INTERVAL = std::chrono::duration_cast<ns>(
    std::chrono::duration<double>{1.0 / UPDATE_HZ});

static volatile bool g_stop = false;
static void handle_sigint(int) { g_stop = true; }

TrueForceWheel::TrueForceWheel(uint16_t vid, uint16_t pid) {
    dev_ = open_device(vid, pid);
}
TrueForceWheel::~TrueForceWheel() { close(); }
void TrueForceWheel::init(bool skip_setup) { send_init(dev_, skip_setup); }
void TrueForceWheel::close() { dev_.close(); }

void TrueForceWheel::tick(const Packet& pkt) {
    send(dev_, pkt, 10);
    recv(dev_, 1);
    reg_        = (reg_ + 1) & 0xFF;
    sample_idx_ += SHIFT_PER_PKT;
}

void TrueForceWheel::stream(
    std::function<std::tuple<float,float,float>(float)> gen_fn,
    double      duration,
    uint8_t     gain,
    std::string label)
{
    if (!label.empty())
        std::printf("\n%s  (Ctrl+C to stop)\n\n", label.c_str());

    auto prev_sig = std::signal(SIGINT, handle_sigint);
    g_stop = false;

    auto t_start = clk::now();
    auto t_next  = t_start;
    int  sent = 0;

    while (true) {
        auto  now     = clk::now();
        float elapsed = std::chrono::duration_cast<fsec>(now - t_start).count();

        if (g_stop) { std::printf("\nStopped.\n"); break; }
        if (duration > 0.0 && elapsed >= static_cast<float>(duration)) break;

        if (now < t_next)
            std::this_thread::sleep_until(t_next);
        t_next += PACKET_INTERVAL;

        auto [kin, amp, freq] = gen_fn(elapsed);
        auto pkt = build_packet(reg_, kin, amp, freq, sample_idx_, gain);
        tick(pkt);
        ++sent;

        if (!label.empty() && sent % 200 == 0)
            std::printf("  %6.2fs  amp=%.4f  freq=%.0fHz\r",
                        (double)elapsed, (double)amp, (double)freq);
    }

    std::signal(SIGINT, prev_sig);
    if (!label.empty()) std::printf("\nDone: %d packets\n", sent);
}

void TrueForceWheel::stream_waveform(
    std::function<float(float)> waveform_fn,
    float       amp,
    double      duration,
    std::string label)
{
    if (!label.empty())
        std::printf("\n%s  (Ctrl+C to stop)\n\n", label.c_str());

    auto prev_sig = std::signal(SIGINT, handle_sigint);
    g_stop = false;

    auto t_start = clk::now();
    auto t_next  = t_start;
    int  sent = 0;

    while (true) {
        auto  now     = clk::now();
        float elapsed = std::chrono::duration_cast<fsec>(now - t_start).count();

        if (g_stop) { std::printf("\nStopped.\n"); break; }
        if (duration > 0.0 && elapsed >= static_cast<float>(duration)) break;

        if (now < t_next)
            std::this_thread::sleep_until(t_next);
        t_next += PACKET_INTERVAL;

        auto pkt = build_packet(reg_, 0.0f, amp, 0.0f, sample_idx_,
                                TF_GAIN_DEFAULT, waveform_fn);
        tick(pkt);
        ++sent;
    }

    std::signal(SIGINT, prev_sig);
    if (!label.empty()) std::printf("\nDone: %d packets\n", sent);
}

void TrueForceWheel::vibrate(float freq, float amp, double duration) {
    char label[64];
    std::snprintf(label, sizeof(label), "vibrate  freq=%.0f Hz  amp=%.4f", freq, amp);
    stream([freq, amp](float) { return std::make_tuple(0.0f, amp, freq); },
           duration, TF_GAIN_DEFAULT, label);
}

void TrueForceWheel::bump(float freq, float decay, float interval, double duration) {
    char label[64];
    std::snprintf(label, sizeof(label), "bump  freq=%.0f Hz  interval=%.2f s", freq, interval);
    stream([freq, decay, interval](float t) {
        float phase = std::fmod(t, interval) / interval;
        float amp   = (phase < 0.3f) ? std::exp(-phase * decay) : 0.0f;
        return std::make_tuple(0.0f, amp, freq);
    }, duration, TF_GAIN_DEFAULT, label);
}

void TrueForceWheel::freq_sweep(float freq_start, float freq_end, float amp, double duration) {
    char label[64];
    std::snprintf(label, sizeof(label), "freq_sweep  %.0f->%.0f Hz  amp=%.2f",
                  freq_start, freq_end, amp);
    float dur_f = static_cast<float>(duration);
    stream([freq_start, freq_end, amp, dur_f](float t) {
        float hz = freq_start + (freq_end - freq_start) * std::min(t / dur_f, 1.0f);
        return std::make_tuple(0.0f, amp, hz);
    }, duration, TF_GAIN_DEFAULT, label);
}

void TrueForceWheel::amp_ramp(float freq, float amp_start, float amp_end, double duration) {
    char label[64];
    std::snprintf(label, sizeof(label), "amp_ramp  %.3f->%.3f  freq=%.0f Hz",
                  amp_start, amp_end, freq);
    float dur_f = static_cast<float>(duration);
    stream([freq, amp_start, amp_end, dur_f](float t) {
        float amp = amp_start + (amp_end - amp_start) * std::min(t / dur_f, 1.0f);
        return std::make_tuple(0.0f, amp, freq);
    }, duration, TF_GAIN_DEFAULT, label);
}

void TrueForceWheel::engine(
    std::function<float(float)> rpm_fn,
    double duration,
    float rpm_min, float rpm_max,
    float freq_min, float freq_max,
    float amp_min,  float amp_max)
{
    stream([=](float t) {
        float rpm  = std::clamp(rpm_fn(t), rpm_min, rpm_max);
        float norm = (rpm - rpm_min) / (rpm_max - rpm_min);
        float freq = freq_min + norm * (freq_max - freq_min);
        float amp  = amp_min  + norm * (amp_max  - amp_min);
        return std::make_tuple(0.0f, amp, freq);
    }, duration, TF_GAIN_DEFAULT, "engine rumble");
}

void TrueForceWheel::stop() {
    auto pkt = build_packet(reg_, 0.0f, 0.0f, 0.0f, sample_idx_);
    tick(pkt);
}

void TrueForceWheel::kinesthetic(float torque, double duration) {
    char label[64];
    std::snprintf(label, sizeof(label), "kinesthetic  torque=%+.2f", torque);
    stream([torque](float) { return std::make_tuple(torque, 0.0f, 0.0f); },
           duration, TF_GAIN_DEFAULT, label);
}

} // namespace trueforce
