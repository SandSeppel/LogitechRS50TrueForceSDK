cmake_minimum_required(VERSION 3.16)
project(logitech-rs50-trueforce-sdk CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})

find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBUSB REQUIRED libusb-1.0)

# ── SDK library ────────────────────────────────────────────────────
add_library(trueforce STATIC
    trueforce/protocol.cpp
    trueforce/device.cpp
    trueforce/wheel.cpp
)

target_include_directories(trueforce
    PUBLIC  ${CMAKE_SOURCE_DIR}          # so examples use <trueforce/wheel.hpp>
    PRIVATE ${LIBUSB_INCLUDE_DIRS}
)

target_link_libraries(trueforce
    PUBLIC  ${LIBUSB_LIBRARIES}
)

target_compile_options(trueforce PRIVATE -Wall -Wextra -O2)

# ── Examples ───────────────────────────────────────────────────────
foreach(example
    engine_rumble
    road_texture
    frequency_sweep
    bumps
    custom_waveforms
    amplitude_sweep
)
    add_executable(${example} examples/${example}.cpp)
    target_link_libraries(${example} PRIVATE trueforce)
endforeach()

# ── Tools ─────────────────────────────────────────────────────────
add_executable(test_modes tools/test_modes.cpp)
target_link_libraries(test_modes PRIVATE trueforce)
