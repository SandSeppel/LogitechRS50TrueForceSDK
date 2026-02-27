"""
trueforce.protocol
==================
Low-level packet construction for the Logitech RS50 TrueForce protocol.

All values verified against 20,531 real CMD=01 packets from USB capture.
"""

import math
import struct

# ── USB identifiers ────────────────────────────────────────────────
VENDOR_ID  = 0x046d
PRODUCT_ID = 0xc276
EP_OUT     = 0x03
EP_IN      = 0x83

# ── Timing ────────────────────────────────────────────────────────
UPDATE_HZ     = 1000.0   # packets per second
PAIRS_PER_PKT = 13       # sample pairs in the sliding-window buffer
SHIFT_PER_PKT = 4        # new pairs appended per packet  (byte[10])
SAMPLE_RATE   = UPDATE_HZ * SHIFT_PER_PKT   # 4000 Hz effective SR

# ── Protocol constants ─────────────────────────────────────────────
TF_GAIN_DEFAULT = 0x0d   # byte[11]: fixed in all PCAP packets, do not change
NEUTRAL_U16     = 0x8000 # centre value for all signed channels

# ── Init sequences ─────────────────────────────────────────────────
def _pkt(*parts: str) -> bytes:
    raw = bytes.fromhex("".join(p.replace(" ", "") for p in parts))
    return raw.ljust(64, b"\x00")

def _hdr(cmd: int, slot: int) -> str:
    return f"01000000 {cmd:02x} {slot:02x}"

CMD05_SLOTS: list[tuple[int, int]] = [
    (0x01,0x00),(0x02,0x30),(0x03,0x01),(0x04,0x02),(0x05,0x03),(0x06,0x04),
    (0x07,0x05),(0x08,0x06),(0x09,0x07),(0x0a,0x08),(0x0b,0x09),(0x0c,0x0a),
    (0x0d,0x0b),(0x0e,0x0c),(0x0f,0x0d),(0x10,0x0e),(0x11,0x0f),(0x12,0x10),
    (0x13,0x11),(0x14,0x12),(0x15,0x13),(0x16,0x14),(0x17,0x15),(0x18,0x16),
    (0x19,0x17),(0x1a,0x18),(0x1b,0x19),(0x1c,0x1a),(0x1d,0x1b),(0x1e,0x1c),
    (0x1f,0x1d),(0x20,0x2b),(0x21,0x2c),(0x22,0x2d),(0x23,0x2e),(0x24,0x2f),
    (0x25,0x31),(0x26,0x32),(0x27,0x33),(0x28,0x34),(0x29,0x35),(0x2a,0x36),
    (0x2b,0x37),(0x2c,0x38),(0x2d,0x39),(0x2e,0x3a),(0x2f,0x3b),(0x30,0x3c),
]

SETUP_CMDS: list[bytes] = [
    _pkt(_hdr(0x0e, 0x32), "00c02845 00000000"),
    _pkt(_hdr(0x07, 0x34), "00000000 00000000"),
    _pkt(_hdr(0x06, 0x36), "01010000 00000000"),
    _pkt(_hdr(0x06, 0x38), "01020000 00000000"),
    _pkt(_hdr(0x06, 0x3a), "01030000 00000000"),
    _pkt(_hdr(0x09, 0x3c), "0202 00000000 0000af43"),
    _pkt(_hdr(0x06, 0x3e), "01040100 00000000"),
    _pkt(_hdr(0x06, 0x40), "01050100 00000000"),
    _pkt(_hdr(0x06, 0x42), "01060100 00000000"),
    _pkt(_hdr(0x04, 0x43), "00000000 00000000"),
    _pkt(_hdr(0x03, 0x44), "00000000 00000000"),
]

SHUTDOWN_PKT: bytes = _pkt(_hdr(0x03, 0x44), "00000000")


# ── Helpers ────────────────────────────────────────────────────────

def float_to_u16(f: float) -> int:
    """Convert a float in [-1.0, 1.0] to a centred uint16."""
    return max(0, min(0xFFFF, int(round(NEUTRAL_U16 + max(-1.0, min(1.0, f)) * 0x7FFF))))


# ── Core packet builder ────────────────────────────────────────────

def build_packet(
    reg:          int,
    kinesthetic:  float = 0.0,
    tf_amp:       float = 0.0,
    tf_freq:      float = 83.0,
    sample_idx:   int   = 0,
    tf_gain:      int   = TF_GAIN_DEFAULT,
    waveform_fn         = None,
) -> bytes:
    """
    Build a 64-byte CMD=01 TrueForce packet.

    Parameters
    ----------
    reg          : Rolling counter 0x00–0xFF (incremented by caller).
    kinesthetic  : Steering torque [-1.0, 1.0].  0.0 = neutral.
    tf_amp       : TrueForce amplitude [0.0, 1.0].
                   PCAP reference (engine rumble) ≈ 0.005.
    tf_freq      : Vibration frequency in Hz (used when waveform_fn is None).
    sample_idx   : Absolute sample counter for the NEWEST pair (pair 12).
                   Must be incremented by SHIFT_PER_PKT each packet.
    tf_gain      : Protocol constant – always 0x0d.  Do not change.
    waveform_fn  : Optional callable (t: float) -> float [-1.0, 1.0].
                   Overrides the built-in sine wave.  t is in seconds.

    Packet layout (PCAP-verified)
    ------------------------------
    [0-3]   01 00 00 00   header
    [4]     0x01          command ID
    [5]     reg           rolling counter
    [6-7]   uint16 LE     kinesthetic CH0  (0x8000 = neutral)
    [8-9]   uint16 LE     kinesthetic CH1  (mirror)
    [10]    0x04          shift count (new pairs per packet)
    [11]    0x0d          protocol constant
    [12-63] 13 × 4 bytes  sliding-window buffer:
              pair j = two identical uint16 LE values
              pair 0  (bytes 12-15)  = oldest  → played next
              pair 12 (bytes 60-63) = newest  → just appended
    """
    pkt = bytearray(64)
    pkt[0] = 0x01
    pkt[4] = 0x01
    pkt[5] = reg & 0xFF

    # Kinesthetic (bytes 6-9)
    if kinesthetic == 0.0:
        pkt[6] = 0x00; pkt[7] = 0x80
        pkt[8] = 0x00; pkt[9] = 0x80
    else:
        kv = float_to_u16(kinesthetic)
        struct.pack_into("<H", pkt, 6, kv)
        struct.pack_into("<H", pkt, 8, kv)

    # TrueForce header
    pkt[10] = SHIFT_PER_PKT     # 0x04
    pkt[11] = tf_gain & 0xFF    # 0x0d

    # Fill all 13 pairs with time-correct samples.
    # pair j corresponds to absolute sample: sample_idx - (PAIRS_PER_PKT-1) + j
    #   j=0  → sample_idx - 12  (oldest)
    #   j=12 → sample_idx       (newest, just written)
    for j in range(PAIRS_PER_PKT):
        abs_s = sample_idx - (PAIRS_PER_PKT - 1) + j
        if tf_amp != 0.0:
            t = abs_s / SAMPLE_RATE
            if waveform_fn is not None:
                raw = max(-1.0, min(1.0, waveform_fn(t))) * tf_amp
            else:
                raw = math.sin(2 * math.pi * tf_freq * t) * tf_amp
            val = max(0, min(0xFFFF, int(0x8000 + raw * 0x7FFF)))
        else:
            val = NEUTRAL_U16
        struct.pack_into("<H", pkt, 12 + j * 4,     val)
        struct.pack_into("<H", pkt, 12 + j * 4 + 2, val)

    return bytes(pkt)
