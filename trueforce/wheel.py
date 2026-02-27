"""
trueforce.wheel
===============
High-level API for TrueForce haptic output on the Logitech RS50.
"""

import math
import time
from typing import Callable, Optional

import usb.core

from .protocol import (
    EP_OUT, EP_IN,
    UPDATE_HZ, PAIRS_PER_PKT, SHIFT_PER_PKT, SAMPLE_RATE,
    TF_GAIN_DEFAULT, NEUTRAL_U16,
    build_packet, SHUTDOWN_PKT,
)
from .device import open_device, close_device, send_init


class TrueForceWheel:
    """
    Context manager for TrueForce haptic output on the Logitech RS50.

    Usage
    -----
    with TrueForceWheel() as wheel:
        wheel.init()
        wheel.vibrate(freq=83.0, amp=0.1, duration=2.0)

    All amplitude values are in the range [0.0, 1.0] where:
      - 0.0  = silence
      - 0.005 = PCAP reference (real engine rumble in BeamNG)
      - 1.0  = full scale (±32767 counts)
    """

    def __init__(self, vendor_id: int = 0x046d, product_id: int = 0xc276):
        self._vendor_id  = vendor_id
        self._product_id = product_id
        self._dev        = None
        self._detached   = []
        self._reg        = 0
        self._sample_idx = PAIRS_PER_PKT - 1  # pre-fill buffer offset

    # ── Context manager ────────────────────────────────────────────

    def __enter__(self):
        self._dev, self._detached = open_device(self._vendor_id, self._product_id)
        return self

    def __exit__(self, *_):
        self.close()

    # ── Setup ──────────────────────────────────────────────────────

    def init(self, skip_setup: bool = True) -> None:
        """
        Send the CMD=05 init sequence.

        Parameters
        ----------
        skip_setup : Skip SETUP_CMDS that cause wheel rotation (default True).
                     Set False if you also need kinesthetic FFB.
        """
        send_init(self._dev, skip_setup=skip_setup)

    def close(self) -> None:
        """Silence output and reattach kernel drivers."""
        if self._dev is not None:
            close_device(self._dev, self._detached)
            self._dev = None

    # ── Core streaming ─────────────────────────────────────────────

    def stream(
        self,
        gen_fn:   Callable[[float], tuple[float, float, float]],
        duration: Optional[float] = None,
        gain:     int = TF_GAIN_DEFAULT,
        label:    str = "",
    ) -> None:
        """
        Stream TrueForce output at 1000 Hz.

        Parameters
        ----------
        gen_fn   : Callable(elapsed_seconds) -> (kinesthetic, tf_amp, tf_freq)
                   kinesthetic : float [-1.0, 1.0]  steering torque
                   tf_amp      : float [0.0, 1.0]   vibration amplitude
                   tf_freq     : float              vibration frequency in Hz
        duration : Seconds to run.  None = run until Ctrl+C.
        gain     : Protocol byte[11].  Keep at 0x0d.
        label    : Optional label printed to stdout.
        """
        interval = 1.0 / UPDATE_HZ
        t_start  = time.monotonic()
        t_next   = t_start
        sent = 0; fb = 0

        if label:
            print(f"\n{label}  (Ctrl+C to stop)\n")

        try:
            while True:
                now     = time.monotonic()
                elapsed = now - t_start
                if duration is not None and elapsed >= duration:
                    break
                if now < t_next:
                    time.sleep(t_next - now)
                t_next += interval

                kin, amp, freq = gen_fn(elapsed)
                pkt = build_packet(
                    self._reg, kin, amp, freq,
                    self._sample_idx, gain,
                )
                try:
                    self._dev.write(EP_OUT, pkt, timeout=10)
                    sent += 1
                except usb.core.USBError as e:
                    print(f"\nUSB error: {e}")
                    break
                try:
                    self._dev.read(EP_IN, 64, timeout=1)
                    fb += 1
                except usb.core.USBError:
                    pass

                self._reg = (self._reg + 1) & 0xFF
                self._sample_idx += SHIFT_PER_PKT

                if label and sent % 200 == 0:
                    print(
                        f"  {elapsed:6.2f}s  amp={amp:.4f}  freq={freq:.0f}Hz  fb={fb}",
                        end="\r",
                    )
        except KeyboardInterrupt:
            print("\nStopped.")

        if label:
            print(f"\nDone: {sent} packets, {fb} responses")

    def stream_waveform(
        self,
        waveform_fn: Callable[[float], float],
        amp:         float,
        duration:    Optional[float] = None,
        gain:        int = TF_GAIN_DEFAULT,
        label:       str = "",
    ) -> None:
        """
        Stream a custom waveform function.

        Parameters
        ----------
        waveform_fn : Callable(t: float) -> float [-1.0, 1.0]
                      Pure waveform shape; amplitude is applied separately.
        amp         : Overall amplitude [0.0, 1.0].
        duration    : Seconds to run.  None = run until Ctrl+C.

        Example
        -------
        # Sawtooth wave at 60 Hz
        wheel.stream_waveform(
            lambda t: (t * 60 % 1.0) * 2 - 1,
            amp=0.05,
            duration=3.0,
        )
        """
        interval = 1.0 / UPDATE_HZ
        t_start  = time.monotonic()
        t_next   = t_start
        sent = 0

        if label:
            print(f"\n{label}  (Ctrl+C to stop)\n")

        try:
            while True:
                now     = time.monotonic()
                elapsed = now - t_start
                if duration is not None and elapsed >= duration:
                    break
                if now < t_next:
                    time.sleep(t_next - now)
                t_next += interval

                pkt = build_packet(
                    self._reg, 0.0, amp, 0.0,
                    self._sample_idx, gain,
                    waveform_fn=waveform_fn,
                )
                try:
                    self._dev.write(EP_OUT, pkt, timeout=10)
                    sent += 1
                except usb.core.USBError as e:
                    print(f"\nUSB error: {e}")
                    break
                try:
                    self._dev.read(EP_IN, 64, timeout=1)
                except usb.core.USBError:
                    pass

                self._reg = (self._reg + 1) & 0xFF
                self._sample_idx += SHIFT_PER_PKT
        except KeyboardInterrupt:
            print("\nStopped.")

        if label:
            print(f"\nDone: {sent} packets")

    # ── High-level effects ─────────────────────────────────────────

    def vibrate(
        self,
        freq:     float,
        amp:      float,
        duration: Optional[float] = None,
        gain:     int = TF_GAIN_DEFAULT,
    ) -> None:
        """
        Continuous sine-wave vibration.

        Parameters
        ----------
        freq     : Frequency in Hz.  Engine range: 40–200 Hz.
        amp      : Amplitude [0.0, 1.0].  PCAP reference: ~0.005.
        duration : Seconds.  None = until Ctrl+C.
        """
        self.stream(
            lambda t: (0.0, amp, freq),
            duration=duration,
            gain=gain,
            label=f"vibrate  freq={freq:.0f}Hz  amp={amp:.4f}",
        )

    def bump(
        self,
        freq:     float = 150.0,
        decay:    float = 20.0,
        interval: float = 0.5,
        duration: float = 6.0,
    ) -> None:
        """
        Repeating decaying impulse — road bump / curb effect.

        Parameters
        ----------
        freq     : Carrier frequency in Hz.
        decay    : Exponential decay rate.  Higher = shorter bump.
        interval : Seconds between bumps.
        duration : Total playback duration.
        """
        def gen(t: float):
            phase = (t % interval) / interval
            amp   = math.exp(-phase * decay) if phase < 0.3 else 0.0
            return 0.0, amp, freq

        self.stream(gen, duration=duration,
                    label=f"bump  freq={freq:.0f}Hz  interval={interval}s")

    def freq_sweep(
        self,
        freq_start: float = 10.0,
        freq_end:   float = 500.0,
        amp:        float = 1.0,
        duration:   float = 10.0,
    ) -> None:
        """
        Linear frequency sweep from freq_start to freq_end.

        Parameters
        ----------
        freq_start : Start frequency in Hz.
        freq_end   : End frequency in Hz.
        amp        : Amplitude [0.0, 1.0].
        duration   : Sweep duration in seconds.
        """
        def gen(t: float):
            hz = freq_start + (freq_end - freq_start) * min(t / duration, 1.0)
            return 0.0, amp, hz

        self.stream(gen, duration=duration,
                    label=f"freq_sweep  {freq_start:.0f}→{freq_end:.0f}Hz  amp={amp:.2f}")

    def amp_ramp(
        self,
        freq:      float = 83.0,
        amp_start: float = 0.0,
        amp_end:   float = 1.0,
        duration:  float = 5.0,
    ) -> None:
        """
        Linearly ramp amplitude from amp_start to amp_end.

        Parameters
        ----------
        freq      : Carrier frequency in Hz.
        amp_start : Starting amplitude [0.0, 1.0].
        amp_end   : Ending amplitude [0.0, 1.0].
        duration  : Ramp duration in seconds.
        """
        def gen(t: float):
            amp = amp_start + (amp_end - amp_start) * min(t / duration, 1.0)
            return 0.0, amp, freq

        self.stream(gen, duration=duration,
                    label=f"amp_ramp  {amp_start:.3f}→{amp_end:.3f}  freq={freq:.0f}Hz")

    def engine(
        self,
        rpm_fn:   Callable[[float], float],
        duration: Optional[float] = None,
        rpm_min:  float = 800.0,
        rpm_max:  float = 8000.0,
        freq_min: float = 40.0,
        freq_max: float = 200.0,
        amp_min:  float = 0.002,
        amp_max:  float = 0.025,
    ) -> None:
        """
        Simulate engine rumble tied to an RPM value over time.

        Parameters
        ----------
        rpm_fn   : Callable(elapsed) -> RPM float.
        duration : Seconds.  None = until Ctrl+C.
        rpm_min/max   : RPM range to map from.
        freq_min/max  : Frequency range to map to.
        amp_min/max   : Amplitude range to map to.

        Example
        -------
        # Linearly ramp RPM from 800 to 6000 over 10 seconds
        wheel.engine(
            rpm_fn=lambda t: 800 + (6000 - 800) * min(t / 10, 1.0),
            duration=10.0,
        )
        """
        def gen(t: float):
            rpm  = max(rpm_min, min(rpm_max, rpm_fn(t)))
            norm = (rpm - rpm_min) / (rpm_max - rpm_min)
            freq = freq_min + norm * (freq_max - freq_min)
            amp  = amp_min  + norm * (amp_max  - amp_min)
            return 0.0, amp, freq

        self.stream(gen, duration=duration, label="engine rumble")

    def stop(self) -> None:
        """Send a single silence packet immediately."""
        pkt = build_packet(self._reg, 0.0, 0.0, 0.0, self._sample_idx)
        try:
            self._dev.write(EP_OUT, pkt, timeout=10)
        except usb.core.USBError:
            pass
        self._reg = (self._reg + 1) & 0xFF
        self._sample_idx += SHIFT_PER_PKT

    def kinesthetic(self, torque: float, duration: float) -> None:
        """
        Apply constant kinesthetic (steering) torque.

        Parameters
        ----------
        torque   : [-1.0, 1.0]  negative = left, positive = right.
        duration : Seconds.
        """
        self.stream(
            lambda t: (torque, 0.0, 0.0),
            duration=duration,
            label=f"kinesthetic  torque={torque:+.2f}",
        )
