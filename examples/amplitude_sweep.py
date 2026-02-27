#!/usr/bin/env python3
"""
examples/amplitude_sweep.py
============================
Steps through amplitude levels at 83 Hz, pausing between each
so you can compare perceptual loudness.

Useful for calibrating what amplitude values feel like on your
specific setup.

Run:  sudo python examples/amplitude_sweep.py
"""

import sys
sys.path.insert(0, ".")

from trueforce import TrueForceWheel

FREQ = 83.0

STEPS = [
    (0.001, "0.1%   — barely perceptible"),
    (0.003, "0.3%"),
    (0.005, "0.5%   — PCAP reference: real BeamNG engine rumble"),
    (0.010, "1%"),
    (0.025, "2.5%"),
    (0.050, "5%"),
    (0.100, "10%"),
    (0.250, "25%"),
    (0.500, "50%"),
    (1.000, "100%   — full scale"),
]

with TrueForceWheel() as wheel:
    wheel.init()
    print(f"\nFrequency: {FREQ} Hz.  Press Enter to advance, Ctrl+C to quit.\n")

    for amp, label in STEPS:
        counts = int(amp * 0x7FFF)
        print(f"  amp={amp:.3f}  ({counts} counts)  {label}")
        wheel.vibrate(freq=FREQ, amp=amp, duration=3.0)
        wheel.stop()
        try:
            input("  → next: ")
        except KeyboardInterrupt:
            break
