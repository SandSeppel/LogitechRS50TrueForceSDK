#!/usr/bin/env python3
"""
examples/custom_waveforms.py
=============================
Shows how to feed arbitrary waveform shapes into TrueForce
using stream_waveform().  Demonstrates sine, sawtooth, square,
triangle, and band-limited noise.

Run:  sudo python examples/custom_waveforms.py
"""

import sys
import math
import random
sys.path.insert(0, ".")

from trueforce import TrueForceWheel


FREQ = 80.0   # carrier frequency for all waveforms
AMP  = 0.08   # moderate amplitude — audible but not harsh
DUR  = 3.0    # seconds per waveform


def sine(t):
    return math.sin(2 * math.pi * FREQ * t)

def sawtooth(t):
    # Rising ramp: -1 → +1 per period
    return 2.0 * ((t * FREQ) % 1.0) - 1.0

def square(t):
    return 1.0 if math.sin(2 * math.pi * FREQ * t) >= 0 else -1.0

def triangle(t):
    phase = (t * FREQ) % 1.0
    return 4.0 * phase - 1.0 if phase < 0.5 else 3.0 - 4.0 * phase

def bandlimited_noise(t):
    # Blend several sine waves at slightly different frequencies to
    # approximate broadband noise while staying within the audio range.
    # (True random noise at 4 kHz SR would sound very different per run,
    #  so we use a deterministic pseudo-noise instead.)
    return (
        math.sin(2 * math.pi * 73  * t) * 0.4 +
        math.sin(2 * math.pi * 113 * t) * 0.3 +
        math.sin(2 * math.pi * 157 * t) * 0.2 +
        math.sin(2 * math.pi * 211 * t) * 0.1
    )


waveforms = [
    (sine,              "sine"),
    (sawtooth,          "sawtooth"),
    (square,            "square"),
    (triangle,          "triangle"),
    (bandlimited_noise, "band-limited noise"),
]

with TrueForceWheel() as wheel:
    wheel.init()

    for fn, name in waveforms:
        print(f"\n  Waveform: {name}  ({FREQ:.0f} Hz, amp={AMP})")
        wheel.stream_waveform(fn, amp=AMP, duration=DUR, label=name)
        wheel.stop()
        import time; time.sleep(0.3)
