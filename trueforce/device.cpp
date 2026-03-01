#include "device.hpp"
#include <cstring>
#include <cstdio>
#include <thread>
#include <chrono>

namespace trueforce {

using namespace std::chrono_literals;

// ── Device::close ──────────────────────────────────────────────────

void Device::close() {
    if (!handle) return;

    // Send shutdown packet
    uint8_t buf[64];
    std::memcpy(buf, SHUTDOWN_PKT.data(), 64);
    int transferred = 0;
    libusb_bulk_transfer(handle, EP_OUT, buf, 64, &transferred, 200);

    // Reattach kernel drivers
    for (int n : detached) {
        libusb_attach_kernel_driver(handle, n);
    }
    detached.clear();

    libusb_close(handle);
    handle = nullptr;

    if (ctx) {
        libusb_exit(ctx);
        ctx = nullptr;
    }

    std::printf("Wheel disabled, interfaces reattached.\n");
}

// ── open_device ────────────────────────────────────────────────────

Device open_device(uint16_t vid, uint16_t pid) {
    Device dev;

    if (int r = libusb_init(&dev.ctx); r < 0)
        throw USBError("libusb_init failed", r);

    dev.handle = libusb_open_device_with_vid_pid(dev.ctx, vid, pid);
    if (!dev.handle) {
        libusb_exit(dev.ctx);
        dev.ctx = nullptr;
        throw DeviceNotFoundError(
            "Device not found. Is the wheel connected? Do you have USB permissions?");
    }

    // Get device info
    libusb_device* d = libusb_get_device(dev.handle);
    std::printf("Device: Bus %d  Addr %d\n",
        libusb_get_bus_number(d),
        libusb_get_device_address(d));

    // Detach kernel drivers from all interfaces
    libusb_config_descriptor* cfg = nullptr;
    libusb_get_active_config_descriptor(d, &cfg);
    if (cfg) {
        for (int i = 0; i < cfg->bNumInterfaces; ++i) {
            if (libusb_kernel_driver_active(dev.handle, i) == 1) {
                if (int r = libusb_detach_kernel_driver(dev.handle, i); r == 0) {
                    dev.detached.push_back(i);
                    std::printf("  Detached interface %d\n", i);
                } else {
                    std::printf("  Interface %d: %s\n", i, libusb_strerror((libusb_error)r));
                }
            }
        }
        libusb_free_config_descriptor(cfg);
    }

    if (int r = libusb_set_configuration(dev.handle, 1); r < 0)
        throw USBError("set_configuration failed", r);

    return dev;
}

// ── send / recv ────────────────────────────────────────────────────

void send(Device& dev, const Packet& pkt, unsigned timeout_ms) {
    uint8_t buf[64];
    std::memcpy(buf, pkt.data(), 64);
    int transferred = 0;
    libusb_bulk_transfer(dev.handle, EP_OUT, buf, 64, &transferred, timeout_ms);
}

std::vector<uint8_t> recv(Device& dev, unsigned timeout_ms) {
    uint8_t buf[64] = {};
    int transferred = 0;
    int r = libusb_bulk_transfer(dev.handle, EP_IN, buf, 64, &transferred, timeout_ms);
    if (r == 0 && transferred > 0)
        return std::vector<uint8_t>(buf, buf + transferred);
    return {};
}

// ── send_init ──────────────────────────────────────────────────────

void send_init(Device& dev, bool skip_setup) {
    // Reset
    send(dev, SHUTDOWN_PKT, 200);
    std::this_thread::sleep_for(50ms);

    std::printf("--- CMD=05 init ---\n");
    int ok = 0;
    for (const auto& [slot, stype] : CMD05_SLOTS) {
        Packet p{};
        p[0] = 0x01;
        p[4] = 0x05;
        p[5] = slot;
        p[6] = stype;
        send(dev, p, 100);

        auto resp = recv(dev, 50);
        if (resp.size() >= 12) {
            float f;
            std::memcpy(&f, resp.data() + 8, 4);
            std::printf("  Slot 0x%02x  param=%.4f\n", slot, f);
        } else {
            std::printf("  Slot 0x%02x  (no response)\n", slot);
        }
        ++ok;
    }
    std::printf("  → %d/%d OK\n", ok, (int)CMD05_SLOTS.size());

    if (skip_setup) {
        std::printf("--- Setup commands skipped ---\n");
        return;
    }

    std::printf("--- Setup commands ---\n");
    for (int i = 0; i < (int)SETUP_CMDS.size(); ++i) {
        const auto& pkt = SETUP_CMDS[i];
        send(dev, pkt, 100);
        std::printf("  [%d] CMD=0x%02x slot=0x%02x\n", i, pkt[4], pkt[5]);
        std::this_thread::sleep_for(3ms);
    }
    std::this_thread::sleep_for(50ms);
    std::printf("  → Setup OK\n");
}

} // namespace trueforce
