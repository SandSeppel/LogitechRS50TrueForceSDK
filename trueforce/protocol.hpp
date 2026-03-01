#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <vector>

namespace trueforce {

// ── USB identifiers ────────────────────────────────────────────────
constexpr uint16_t VENDOR_ID  = 0x046d;
constexpr uint16_t PRODUCT_ID = 0xc276;
constexpr uint8_t  EP_OUT     = 0x03;
constexpr uint8_t  EP_IN      = 0x83;

// ── Timing ────────────────────────────────────────────────────────
constexpr double  UPDATE_HZ     = 1000.0;
constexpr int     PAIRS_PER_PKT = 13;
constexpr int     SHIFT_PER_PKT = 4;
constexpr double  SAMPLE_RATE   = UPDATE_HZ * SHIFT_PER_PKT;  // 4000 Hz

// ── Protocol constants ─────────────────────────────────────────────
constexpr uint8_t  TF_GAIN_DEFAULT = 0x0d;
constexpr uint16_t NEUTRAL_U16     = 0x8000;

// ── Packet type ────────────────────────────────────────────────────
using Packet = std::array<uint8_t, 64>;

// ── Init sequences ─────────────────────────────────────────────────
struct SlotInit {
    uint8_t slot;
    uint8_t stype;
};

extern const std::vector<SlotInit> CMD05_SLOTS;
extern const std::vector<Packet>   SETUP_CMDS;
extern const Packet                SHUTDOWN_PKT;

// ── Helpers ────────────────────────────────────────────────────────
uint16_t float_to_u16(float f);

// ── Core packet builder ────────────────────────────────────────────
/**
 * Build a 64-byte CMD=01 TrueForce packet.
 *
 * @param reg          Rolling counter 0x00–0xFF.
 * @param kinesthetic  Steering torque [-1, 1].  0 = neutral.
 * @param tf_amp       Vibration amplitude [0, 1].  PCAP ref ≈ 0.005.
 * @param tf_freq      Vibration frequency in Hz.
 * @param sample_idx   Absolute sample index of the NEWEST pair.
 *                     Increment by SHIFT_PER_PKT each packet.
 * @param tf_gain      Protocol constant — always 0x0d.
 * @param waveform_fn  Optional custom waveform shape: (t_seconds) -> [-1, 1].
 *                     If nullptr, a sine wave is used.
 */
Packet build_packet(
    uint8_t  reg,
    float    kinesthetic  = 0.0f,
    float    tf_amp       = 0.0f,
    float    tf_freq      = 83.0f,
    int      sample_idx   = 0,
    uint8_t  tf_gain      = TF_GAIN_DEFAULT,
    std::function<float(float)> waveform_fn = nullptr
);

} // namespace trueforce
