"""
trueforce
=========
Python SDK for TrueForce haptic feedback on the Logitech RS50 / G Pro Racing Wheel.
"""

from .wheel import TrueForceWheel
from .protocol import (
    build_packet,
    VENDOR_ID, PRODUCT_ID,
    UPDATE_HZ, SAMPLE_RATE, SHIFT_PER_PKT, PAIRS_PER_PKT,
    TF_GAIN_DEFAULT,
)
from .device import DeviceNotFoundError

__all__ = [
    "TrueForceWheel",
    "build_packet",
    "DeviceNotFoundError",
    "VENDOR_ID", "PRODUCT_ID",
    "UPDATE_HZ", "SAMPLE_RATE", "SHIFT_PER_PKT", "PAIRS_PER_PKT",
    "TF_GAIN_DEFAULT",
]
