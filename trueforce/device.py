"""
trueforce.device
================
USB device open/close and init-sequence helpers.
"""

import struct
import time

import usb.core
import usb.util

from .protocol import (
    VENDOR_ID, PRODUCT_ID, EP_OUT, EP_IN,
    CMD05_SLOTS, SETUP_CMDS, SHUTDOWN_PKT,
    _hdr, _pkt,
)


class DeviceNotFoundError(RuntimeError):
    pass


def open_device(vendor_id: int = VENDOR_ID, product_id: int = PRODUCT_ID):
    """
    Find the wheel, detach kernel drivers, and set USB configuration.

    Returns
    -------
    (dev, detached_interfaces)
    """
    dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)
    if dev is None:
        raise DeviceNotFoundError(
            f"Device {vendor_id:#06x}:{product_id:#06x} not found. "
            "Is the wheel connected? Do you have USB permissions?"
        )
    print(f"Device: Bus {dev.bus}  Addr {dev.address}")
    detached = []
    for cfg in dev:
        for intf in cfg:
            n = intf.bInterfaceNumber
            try:
                if dev.is_kernel_driver_active(n):
                    dev.detach_kernel_driver(n)
                    detached.append(n)
                    print(f"  Detached interface {n}")
            except usb.core.USBError as e:
                print(f"  Interface {n}: {e}")
    dev.set_configuration()
    return dev, detached


def close_device(dev, detached: list[int]) -> None:
    """Send shutdown packet and reattach kernel drivers."""
    try:
        dev.write(EP_OUT, SHUTDOWN_PKT, timeout=200)
    except Exception:
        pass
    for n in detached:
        try:
            dev.attach_kernel_driver(n)
        except Exception:
            pass
    print("Wheel disabled, interfaces reattached.")


def send_init(dev, skip_setup: bool = True) -> None:
    """
    Send the CMD=05 slot-configuration sequence and optional setup commands.

    Parameters
    ----------
    skip_setup : If True (default), skip SETUP_CMDS that cause wheel rotation.
                 Set to False only if you need full kinesthetic FFB support.
    """
    # Reset
    try:
        dev.write(EP_OUT, SHUTDOWN_PKT, timeout=200)
        time.sleep(0.05)
    except Exception:
        pass

    print("--- CMD=05 init ---")
    ok = 0
    for slot, stype in CMD05_SLOTS:
        pkt = _pkt(_hdr(0x05, slot), f"{stype:02x}00 00000000 00000000")
        dev.write(EP_OUT, pkt, timeout=100)
        try:
            resp = bytes(dev.read(EP_IN, 64, timeout=50))
            if len(resp) >= 12:
                f_val = struct.unpack_from("<f", resp, 8)[0]
                print(f"  Slot 0x{slot:02x}  param={f_val:.4f}")
            ok += 1
        except usb.core.USBError:
            print(f"  Slot 0x{slot:02x}  (no response)")
    print(f"  → {ok}/{len(CMD05_SLOTS)} OK")

    if skip_setup:
        print("--- Setup commands skipped ---")
        return

    print("--- Setup commands ---")
    for i, pkt in enumerate(SETUP_CMDS):
        dev.write(EP_OUT, pkt, timeout=100)
        print(f"  [{i}] CMD=0x{pkt[4]:02x} slot=0x{pkt[5]:02x}")
        time.sleep(0.003)
    time.sleep(0.05)
    print("  → Setup OK")
