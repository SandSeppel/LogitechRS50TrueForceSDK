#!/usr/bin/env python3
"""
tools/test_modes.py
===================
Diagnostic test modes — all implemented via the TrueForce SDK.

Usage:  sudo python tools/test_modes.py [mode]

Modes
-----
  engine     83 Hz sine: 3 s at 100%, then PCAP reference amplitude (0.5%)
  ampsweep   Step through 0.1%–100% amplitude at 83 Hz (interactive)
  sweep      Frequency sweep 10 → 500 Hz at full amplitude
  bump       Decaying impulses every 500 ms at 150 Hz
  freq       Slow frequency sweep 20 → 500 Hz at 30%
  silence    Send neutral packets for 3 seconds
  scan       Interactive: isolate individual buffer pairs (protocol debug)
  bisect     Interactive: identify which setup command causes wheel rotation
"""

import math
import struct
import sys
import time
sys.path.insert(0, ".")

from trueforce import TrueForceWheel
from trueforce.protocol import (
    EP_OUT, EP_IN, UPDATE_HZ, PAIRS_PER_PKT, SHIFT_PER_PKT, SAMPLE_RATE,
    TF_GAIN_DEFAULT, NEUTRAL_U16, build_packet,
    CMD05_SLOTS, SETUP_CMDS, SHUTDOWN_PKT, _hdr, _pkt,
)
from trueforce.device import open_device, close_device, send_init
import usb.core


# ── Individual test modes ──────────────────────────────────────────

def mode_engine(wheel: TrueForceWheel):
    def gen(t):
        amp = 1.0 if t < 3.0 else 0.005
        return 0.0, amp, 83.0
    wheel.stream(gen, duration=8.0,
                 label="engine: 3s@100% then PCAP reference (0.5%)")


def mode_sweep(wheel: TrueForceWheel):
    wheel.freq_sweep(10.0, 500.0, amp=1.0, duration=10.0)


def mode_bump(wheel: TrueForceWheel):
    wheel.bump(freq=150.0, decay=20.0, interval=0.5, duration=6.0)


def mode_ampsweep(wheel: TrueForceWheel):
    steps = [
        (0.001, "0.1%"),
        (0.003, "0.3%"),
        (0.005, "0.5% — PCAP reference"),
        (0.01,  "1%"),
        (0.05,  "5%"),
        (0.10,  "10%"),
        (0.25,  "25%"),
        (0.50,  "50%"),
        (1.00,  "100% full scale"),
    ]
    print("\n=== Amplitude sweep @ 83 Hz ===")
    for amp, label in steps:
        print(f"\n  {label}  ({int(amp*0x7FFF)} counts)")
        wheel.vibrate(freq=83.0, amp=amp, duration=3.0)
        wheel.stop()
        try:
            input("  Enter=next, Ctrl+C=quit: ")
        except KeyboardInterrupt:
            break


def mode_freq(wheel: TrueForceWheel):
    wheel.freq_sweep(20.0, 500.0, amp=0.30, duration=15.0)


def mode_silence(wheel: TrueForceWheel):
    wheel.stream(lambda t: (0.0, 0.0, 0.0), duration=3.0, label="silence")


def mode_scan(dev):
    """Raw scan of individual buffer pairs — uses low-level USB directly."""
    print("\n=== SCAN: individual pairs in the 13-pair buffer ===\n")
    reg = 0
    sample_idx = PAIRS_PER_PKT - 1
    interval = 1.0 / UPDATE_HZ

    for target_pair in list(range(13)) + [-1]:
        label = "ALL 13 pairs" if target_pair == -1 \
            else f"Pair {target_pair} (bytes {12+target_pair*4}–{15+target_pair*4})"
        input(f"  Enter → {label}: ")
        t_start = time.monotonic()
        t_next  = t_start
        sent = 0
        while time.monotonic() - t_start < 2.0:
            now = time.monotonic()
            if now < t_next:
                time.sleep(t_next - now)
            t_next += interval
            pkt = bytearray(64)
            pkt[0] = 0x01; pkt[4] = 0x01; pkt[5] = reg & 0xFF
            pkt[6] = 0x00; pkt[7] = 0x80; pkt[8] = 0x00; pkt[9] = 0x80
            pkt[10] = 0x04; pkt[11] = TF_GAIN_DEFAULT
            for j in range(13):
                struct.pack_into("<H", pkt, 12+j*4,   NEUTRAL_U16)
                struct.pack_into("<H", pkt, 12+j*4+2, NEUTRAL_U16)
            if target_pair == -1:
                for j in range(13):
                    tv  = (sample_idx - 12 + j) / SAMPLE_RATE
                    val = max(0, min(0xFFFF, int(0x8000 + 0x7FFF * math.sin(2*math.pi*83*tv))))
                    struct.pack_into("<H", pkt, 12+j*4,   val)
                    struct.pack_into("<H", pkt, 12+j*4+2, val)
            else:
                tv  = sample_idx / SAMPLE_RATE
                val = max(0, min(0xFFFF, int(0x8000 + 0x7FFF * math.sin(2*math.pi*83*tv))))
                struct.pack_into("<H", pkt, 12+target_pair*4,   val)
                struct.pack_into("<H", pkt, 12+target_pair*4+2, val)
            try:
                dev.write(EP_OUT, bytes(pkt), timeout=10)
                sent += 1
            except Exception:
                break
            try:
                dev.read(EP_IN, 64, timeout=1)
            except Exception:
                pass
            reg = (reg + 1) & 0xFF
            sample_idx += SHIFT_PER_PKT
        print(f"  {sent} packets sent")


def mode_bisect(dev):
    """Interactive binary search to find which setup command causes rotation."""
    print("\n=== BISECT: find setup command that causes rotation ===\n")
    reg = 0
    sample_idx = PAIRS_PER_PKT - 1
    interval = 1.0 / UPDATE_HZ

    def neutral_loop(seconds, label):
        nonlocal reg, sample_idx
        print(f"  [{label}] {seconds}s...", end="", flush=True)
        t = time.monotonic()
        while time.monotonic() - t < seconds:
            pkt = build_packet(reg, 0.0, 1.0, 83.0, sample_idx)
            try:
                dev.write(EP_OUT, pkt, timeout=10)
            except Exception:
                break
            try:
                dev.read(EP_IN, 64, timeout=1)
            except Exception:
                pass
            reg = (reg + 1) & 0xFF
            sample_idx += SHIFT_PER_PKT
            time.sleep(interval)
        print(" done")

    neutral_loop(3, "baseline")
    for i, pkt in enumerate(SETUP_CMDS):
        cmd = pkt[4]; slot = pkt[5]
        print(f"\n  Sending CMD=0x{cmd:02x} slot=0x{slot:02x}...")
        dev.write(EP_OUT, pkt, timeout=100)
        time.sleep(0.003)
        neutral_loop(3, f"after CMD[{i}] 0x{cmd:02x}")
        ans = input(f"  Rotating after CMD[{i}]? (y/n/q): ").strip().lower()
        if ans == "q":
            break
        if ans == "y":
            print(f"  *** CULPRIT: CMD[{i}] = 0x{cmd:02x} slot=0x{slot:02x} ***")
            print(f"  Payload: {pkt[:12].hex()}")
            break
    else:
        print("\nAll setup commands OK — none caused rotation.")


# ── Dispatch ───────────────────────────────────────────────────────

MODES = {
    "engine":   (True,  mode_engine,   "83 Hz: 3s full, then PCAP reference"),
    "ampsweep": (True,  mode_ampsweep, "amplitude steps 0.1%–100% @ 83 Hz"),
    "sweep":    (True,  mode_sweep,    "frequency sweep 10→500 Hz"),
    "bump":     (True,  mode_bump,     "decaying impulses @ 150 Hz"),
    "freq":     (True,  mode_freq,     "freq sweep 20→500 Hz @ 30%"),
    "silence":  (True,  mode_silence,  "neutral output for 3 s"),
    "scan":     (False, mode_scan,     "isolate buffer pairs (debug)"),
    "bisect":   (False, mode_bisect,   "find rotation-causing setup command"),
}


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "engine"
    if mode not in MODES:
        print("Available modes:")
        for name, (_, _, desc) in MODES.items():
            print(f"  {name:10s}  {desc}")
        sys.exit(1)

    uses_wheel, fn, desc = MODES[mode]
    print(f"Mode: {mode} — {desc}\n")

    if uses_wheel:
        with TrueForceWheel() as wheel:
            wheel.init()
            fn(wheel)
    else:
        # scan/bisect need raw device access
        dev, detached = open_device()
        try:
            send_init(dev, skip_setup=(mode == "scan"))
            fn(dev)
        finally:
            close_device(dev, detached)


if __name__ == "__main__":
    main()
