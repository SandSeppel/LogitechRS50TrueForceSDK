#!/usr/bin/env python3
"""
examples/road_texture.py
========================
Simulates different road surfaces back-to-back:

  smooth tarmac  → low-frequency, very low amplitude
  rough tarmac   → slightly higher amplitude
  cobblestone    → medium amplitude, choppy waveform
  gravel         → higher amplitude, noisy waveform
  rumble strip   → periodic burst pattern

Run:  sudo python examples/road_texture.py
"""

import sys
import math
import random
sys.path.insert(0, ".")

from trueforce import TrueForceWheel


# ── Surface generators ─────────────────────────────────────────────
# Each returns (kinesthetic, tf_amp, tf_freq) from elapsed time t.

def smooth_tarmac(t):
    return 0.0, 0.002, 80.0

def rough_tarmac(t):
    return 0.0, 0.006, 95.0

def cobblestone(t):
    # Periodic hard knocks at ~8 Hz carrier
    base = math.sin(2 * math.pi * 8 * t)
    amp  = 0.04 * max(0.0, base)  # only positive half-cycles
    return 0.0, amp, 120.0

def gravel(t):
    # Two overlapping frequencies to approximate randomness
    a = math.sin(2 * math.pi * 75 * t) * 0.5
    b = math.sin(2 * math.pi * 130 * t) * 0.5
    amp = abs(a + b) * 0.05
    return 0.0, amp, 100.0

def rumble_strip(t):
    # 5 Hz bursts of vibration
    phase = (t % 0.2) / 0.2
    amp   = 0.12 if phase < 0.4 else 0.0
    return 0.0, amp, 85.0


surfaces = [
    (smooth_tarmac, 3.0, "smooth tarmac"),
    (rough_tarmac,  3.0, "rough tarmac"),
    (cobblestone,   3.0, "cobblestone"),
    (gravel,        3.0, "gravel"),
    (rumble_strip,  3.0, "rumble strip"),
]

with TrueForceWheel() as wheel:
    wheel.init()
    for gen_fn, dur, name in surfaces:
        print(f"\n  Surface: {name}")
        wheel.stream(gen_fn, duration=dur)
        wheel.stop()
