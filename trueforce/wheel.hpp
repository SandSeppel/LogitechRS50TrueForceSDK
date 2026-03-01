#pragma once
#include "device.hpp"
#include <functional>
#include <optional>
#include <string>

namespace trueforce {

/**
 * High-level API for TrueForce haptic output on the Logitech RS50.
 *
 * RAII wrapper — opens the device on construction, closes on destruction.
 *
 * Usage
 * -----
 *   TrueForceWheel wheel;
 *   wheel.init();
 *   wheel.vibrate(83.0f, 0.1f, 2.0);
 *
 * All amplitude values are [0.0, 1.0]:
 *   0.0   = silence
 *   0.005 = PCAP reference (real engine rumble in BeamNG)
 *   1.0   = full scale
 */
class TrueForceWheel {
public:
    explicit TrueForceWheel(uint16_t vid = VENDOR_ID, uint16_t pid = PRODUCT_ID);
    ~TrueForceWheel();

    // Non-copyable, movable
    TrueForceWheel(const TrueForceWheel&)            = delete;
    TrueForceWheel& operator=(const TrueForceWheel&) = delete;
    TrueForceWheel(TrueForceWheel&&)                 = default;

    // ── Setup ──────────────────────────────────────────────────────

    /**
     * Send CMD=05 init sequence.
     * @param skip_setup  Skip SETUP_CMDS that cause wheel rotation (default true).
     */
    void init(bool skip_setup = true);

    /** Silence output and close USB device. */
    void close();

    // ── Core streaming ─────────────────────────────────────────────

    /**
     * Stream TrueForce output at 1000 Hz using a generator function.
     *
     * @param gen_fn    Called once per packet with elapsed seconds.
     *                  Returns {kinesthetic [-1,1], tf_amp [0,1], tf_freq [Hz]}.
     * @param duration  Seconds to run.  0 = run until Ctrl+C / stopped.
     * @param gain      Protocol constant — keep at TF_GAIN_DEFAULT (0x0d).
     * @param label     Optional label printed to stdout.
     */
    void stream(
        std::function<std::tuple<float,float,float>(float)> gen_fn,
        double      duration = 0.0,
        uint8_t     gain     = TF_GAIN_DEFAULT,
        std::string label    = ""
    );

    /**
     * Stream a custom waveform shape function.
     *
     * @param waveform_fn  (t_seconds) -> float [-1, 1].  Pure shape, no amplitude.
     * @param amp          Overall amplitude [0, 1].
     * @param duration     Seconds to run.  0 = until Ctrl+C.
     * @param label        Optional label.
     */
    void stream_waveform(
        std::function<float(float)> waveform_fn,
        float       amp,
        double      duration = 0.0,
        std::string label    = ""
    );

    // ── High-level effects ─────────────────────────────────────────

    /**
     * Continuous sine-wave vibration.
     * @param freq     Hz.  Engine: 40–200 Hz.
     * @param amp      [0, 1].  PCAP reference: ~0.005.
     * @param duration Seconds.  0 = until Ctrl+C.
     */
    void vibrate(float freq, float amp, double duration = 0.0);

    /**
     * Repeating decaying impulse — road bump / curb effect.
     * @param freq      Carrier Hz.
     * @param decay     Exponential decay rate.  Higher = shorter.
     * @param interval  Seconds between bumps.
     * @param duration  Total playback seconds.
     */
    void bump(
        float freq     = 150.0f,
        float decay    = 20.0f,
        float interval = 0.5f,
        double duration = 6.0
    );

    /**
     * Linear frequency sweep.
     * @param freq_start  Start Hz.
     * @param freq_end    End Hz.
     * @param amp         Amplitude [0, 1].
     * @param duration    Seconds.
     */
    void freq_sweep(
        float  freq_start = 10.0f,
        float  freq_end   = 500.0f,
        float  amp        = 1.0f,
        double duration   = 10.0
    );

    /**
     * Linearly ramp amplitude.
     * @param freq       Carrier Hz.
     * @param amp_start  Start amplitude [0, 1].
     * @param amp_end    End amplitude [0, 1].
     * @param duration   Seconds.
     */
    void amp_ramp(
        float  freq      = 83.0f,
        float  amp_start = 0.0f,
        float  amp_end   = 1.0f,
        double duration  = 5.0
    );

    /**
     * Engine rumble tied to an RPM value over time.
     * @param rpm_fn    (elapsed_seconds) -> RPM float.
     * @param duration  Seconds.  0 = until Ctrl+C.
     * @param rpm_min/max    RPM range to map from.
     * @param freq_min/max   Frequency range to map to (Hz).
     * @param amp_min/max    Amplitude range to map to [0, 1].
     */
    void engine(
        std::function<float(float)> rpm_fn,
        double duration  = 0.0,
        float  rpm_min   = 800.0f,
        float  rpm_max   = 8000.0f,
        float  freq_min  = 40.0f,
        float  freq_max  = 200.0f,
        float  amp_min   = 0.002f,
        float  amp_max   = 0.025f
    );

    /** Send a single silence packet immediately. */
    void stop();

    /**
     * Apply constant kinesthetic (steering) torque.
     * @param torque   [-1, 1]  negative = left, positive = right.
     * @param duration Seconds.
     */
    void kinesthetic(float torque, double duration);

private:
    Device  dev_;
    uint8_t reg_        = 0;
    int     sample_idx_ = PAIRS_PER_PKT - 1;

    void tick(const Packet& pkt);
};

} // namespace trueforce
