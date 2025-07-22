# add source files
add_executable(${PROJECT_NAME}	
	main.c
	epaper_handler.c
	udp_handler.c
	miniz.c
    globals.c
    epaper_driver.c
    rtc.c
)

# linker options
target_link_options(${PROJECT_NAME} 
    PRIVATE "LINKER:--print-memory-usage"
)

target_compile_definitions(${PROJECT_NAME} PRIVATE
        WIFI_SSID=\"${WIFI_SSID}\"
        WIFI_PASSWORD=\"${WIFI_PASSWORD}\"
        )
target_include_directories(${PROJECT_NAME} PRIVATE
        ${CMAKE_CURRENT_LIST_DIR}
        ${CMAKE_CURRENT_LIST_DIR}/../include
        )
target_link_libraries(${PROJECT_NAME}
        pico_cyw43_arch_lwip_sys_freertos
        pico_stdlib
        pico_lwip_iperf
        FreeRTOS-Kernel-Heap4 # FreeRTOS kernel and dynamic heap
        hardware_gpio
        hardware_sleep
        hardware_adc
        hardware_spi
        hardware_i2c
        )
pico_add_extra_outputs(${PROJECT_NAME})
# Enable usb output, disable uart output
pico_enable_stdio_usb(${PROJECT_NAME} 0)
pico_enable_stdio_uart(${PROJECT_NAME} 1)
