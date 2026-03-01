#pragma once
#include "protocol.hpp"
#include <libusb-1.0/libusb.h>
#include <stdexcept>
#include <vector>
#include <string>

namespace trueforce {

// ── Exceptions ─────────────────────────────────────────────────────

struct DeviceNotFoundError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

struct USBError : std::runtime_error {
    int code;
    USBError(const std::string& msg, int code)
        : std::runtime_error(msg + ": " + libusb_strerror(static_cast<libusb_error>(code)))
        , code(code) {}
};

// ── Device handle ──────────────────────────────────────────────────

struct Device {
    libusb_context*       ctx      = nullptr;
    libusb_device_handle* handle   = nullptr;
    std::vector<int>      detached;

    // Non-copyable
    Device(const Device&)            = delete;
    Device& operator=(const Device&) = delete;

    Device() = default;
    ~Device() { close(); }

    // Move: null out source so its destructor doesn't double-free
    Device(Device&& o) noexcept
        : ctx(o.ctx), handle(o.handle), detached(std::move(o.detached))
    {
        o.ctx    = nullptr;
        o.handle = nullptr;
    }

    Device& operator=(Device&& o) noexcept {
        if (this != &o) {
            close();
            ctx      = o.ctx;
            handle   = o.handle;
            detached = std::move(o.detached);
            o.ctx    = nullptr;
            o.handle = nullptr;
        }
        return *this;
    }

    void close();
};

// ── Functions ──────────────────────────────────────────────────────

Device open_device(uint16_t vid = VENDOR_ID, uint16_t pid = PRODUCT_ID);
void send(Device& dev, const Packet& pkt, unsigned timeout_ms = 10);
std::vector<uint8_t> recv(Device& dev, unsigned timeout_ms = 1);
void send_init(Device& dev, bool skip_setup = true);

} // namespace trueforce
