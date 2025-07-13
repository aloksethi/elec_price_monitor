cmake_minimum_required(VERSION 3.13)
set(FREERTOS_KERNEL_PATH "${CMAKE_CURRENT_LIST_DIR}/FreeRTOS-Kernel")

#Set the global output directory for ALL Pico SDK generated files (like .uf2)
# This *must* be set BEFORE pico_sdk_init()
set(PICO_OUT_DIR "${CMAKE_BINARY_DIR}") # Or PICO_BUILD_OUTPUT_DIR, try PICO_OUT_DIR first

# If you also want ALL executables from ALL subdirectories to go to the top level
# (which is often desired for embedded projects with a single main firmware),
# set this globally too. This needs to be set early.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}") # For static libraries
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}") # For shared libraries



# Pull in SDK (must be before project)
include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)
include($ENV{PICO_EXTRAS_PATH}/external/pico_extras_import.cmake)
# Pull in FreeRTOS
#include($ENV{FREERTOS_KERNEL_PATH}/portable/ThirdParty/GCC/RP2040/FreeRTOS_Kernel_import.cmake)
include(${FREERTOS_KERNEL_PATH}/portable/ThirdParty/GCC/RP2040/FreeRTOS_Kernel_import.cmake)

project(elec-price-mon C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
    
# Initialize the SDK
pico_sdk_init()

add_subdirectory(src)

set(WIFI_SSID "${WIFI_SSID}" CACHE INTERNAL "WiFi SSID")
set(WIFI_PASSWORD "${WIFI_PASSWORD}" CACHE INTERNAL "WiFi password")
if ("${WIFI_SSID}" STREQUAL "")
	message(FATAL_ERROR "WIFI_SSID is not defined")
endif()
if ("${WIFI_PASSWORD}" STREQUAL "")
	message(FATAL_ERROR "WIFI_PASSWORD is not defined")
endif()
#include(FreeRTOS_Kernel_import.cmake)

add_compile_options(-Wall
        -Wno-format          # int != int32_t as far as the compiler is concerned because gcc has int32_t as long int
        -Wno-unused-function # we have some for the docs that aren't called
        )
if (CMAKE_C_COMPILER_ID STREQUAL "GNU")
    add_compile_options(-Wno-maybe-uninitialized)
endif()
