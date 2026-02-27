#!/usr/bin/env python3
"""
examples/frequency_sweep.py
============================
Sweeps from 10 Hz to 500 Hz at constant amplitude so you can feel
the entire TrueForce frequency range in one go.

Then does a second pass at a realistic amplitude (0.02) to hear
the difference between full-scale and real-world levels.

Run:  sudo python examples/frequency_sweep.py
"""

import sys
sys.path.insert(0, ".")

from trueforce import TrueForceWheel


with TrueForceWheel() as wheel:
    wheel.init()

    print("\n=== Pass 1: full amplitude (1.0) — hear the full range ===")
    wheel.freq_sweep(
        freq_start=10.0,
        freq_end=500.0,
        amp=1.0,
        duration=10.0,
    )

    wheel.stop()
    import time; time.sleep(0.5)

    print("\n=== Pass 2: realistic amplitude (0.02) — like real gameplay ===")
    wheel.freq_sweep(
        freq_start=10.0,
        freq_end=500.0,
        amp=0.02,
        duration=10.0,
    )
