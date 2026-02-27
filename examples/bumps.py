#!/usr/bin/env python3
"""
examples/bumps.py
=================
Demonstrates several impact / bump variations:

  kerb     — hard, sharp, fast decay
  pothole  — medium decay, slightly lower frequency
  rumble   — slow repeating mild bumps like expansion joints
  crash    — single hard impact

Run:  sudo python examples/bumps.py
"""

import sys
import math
sys.path.insert(0, ".")

from trueforce import TrueForceWheel


def one_shot_impact(wheel, freq=200.0, amp=0.8, decay=30.0, duration=0.5):
    """Play a single decaying impact and return."""
    wheel.stream(
        lambda t: (0.0, amp * math.exp(-t * decay), freq),
        duration=duration,
    )


with TrueForceWheel() as wheel:
    wheel.init()

    print("\n--- Kerb strike (every 600 ms, hard) ---")
    wheel.bump(freq=180.0, decay=40.0, interval=0.6, duration=5.0)
    wheel.stop()

    print("\n--- Pothole (every 1.5 s, medium) ---")
    wheel.bump(freq=120.0, decay=18.0, interval=1.5, duration=6.0)
    wheel.stop()

    print("\n--- Expansion joints (every 300 ms, gentle) ---")
    wheel.bump(freq=80.0, decay=12.0, interval=0.3, duration=5.0)
    wheel.stop()

    import time; time.sleep(0.5)

    print("\n--- Single crash impact ---")
    one_shot_impact(wheel, freq=200.0, amp=1.0, decay=15.0, duration=1.0)
