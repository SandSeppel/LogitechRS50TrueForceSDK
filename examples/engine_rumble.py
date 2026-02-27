#!/usr/bin/env python3
"""
examples/engine_rumble.py
=========================
Simulates engine vibration with rising RPM.

- 0–5 s : RPM ramps from idle (800) to redline (7000)
- 5–8 s : holds at redline
- 8–10s : RPM drops back to idle

Frequency and amplitude are both mapped from RPM, matching
the ~0.005 amplitude captured from real BeamNG gameplay.

Run:  sudo python examples/engine_rumble.py
"""

import sys
import math
sys.path.insert(0, ".")

from trueforce import TrueForceWheel


def rpm_curve(t: float) -> float:
    """Simple RPM profile over 10 seconds."""
    if t < 5.0:
        return 800 + (7000 - 800) * (t / 5.0)
    elif t < 8.0:
        return 7000
    else:
        return 7000 - (7000 - 800) * ((t - 8.0) / 2.0)


with TrueForceWheel() as wheel:
    wheel.init()
    wheel.engine(
        rpm_fn=rpm_curve,
        duration=10.0,
        rpm_min=800,
        rpm_max=7000,
        freq_min=40.0,
        freq_max=180.0,
        amp_min=0.002,
        amp_max=0.025,
    )
