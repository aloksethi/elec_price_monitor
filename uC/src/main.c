/**
 * Copyright (c) 2022 Raspberry Pi (Trading) Ltd.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include "pico/cyw43_arch.h"
#include "pico/stdlib.h"

#include "lwip/netif.h"
#include "lwip/ip4_addr.h"
#include "lwip/apps/lwiperf.h"

#include "FreeRTOS.h"
#include "task.h"
#include "config.h"



void udp_task(void *params);
void epaper_task(void *params);

 #if 0
// Report IP results and exit
static void iperf_report(void *arg, enum lwiperf_report_type report_type,
                         const ip_addr_t *local_addr, u16_t local_port, const ip_addr_t *remote_addr, u16_t remote_port,
                         u32_t bytes_transferred, u32_t ms_duration, u32_t bandwidth_kbitpsec) {
    static uint32_t total_iperf_megabytes = 0;
    uint32_t mbytes = bytes_transferred / 1024 / 1024;
    float mbits = bandwidth_kbitpsec / 1000.0;

    total_iperf_megabytes += mbytes;

    printf("Completed iperf transfer of %d MBytes @ %.1f Mbits/sec\n", mbytes, mbits);
    printf("Total iperf megabytes since start %d Mbytes\n", total_iperf_megabytes);

    return;
}
#endif

void blink_task(__unused void *params) {
    bool on = false;
    printf("blink_task starts\n");
    while (true) {
        cyw43_arch_gpio_put(0, on);
        on = !on;
        vTaskDelay(1000);
	//printf("blinking now from core %d\n", portGET_CORE_ID());
    }
}

void create_rest_tasks(void)
{
    xTaskCreate(blink_task, "Blink_Task", STACK_SIZE_BLINK_TASK, NULL, PRIO_BLINK_TASK, NULL);
    xTaskCreate(udp_task, "UDP_Task", STACK_SIZE_UDP_TASK, NULL, PRIO_UDP_TASK, NULL);
    xTaskCreate(epaper_task, "ePaper_Task", STACK_SIZE_EPAPER_TASK, NULL, PRIO_EPAPER_TASK, NULL);

	return;	
}
void cy43_task(__unused void *params) {
    if (cyw43_arch_init()) {
        printf("failed to initialise\n");
        exit(1);
        return;
    }
    cyw43_arch_enable_sta_mode();
    printf("Connecting to Wi-Fi...\n");
    if (cyw43_arch_wifi_connect_timeout_ms(WIFI_SSID, WIFI_PASSWORD, CYW43_AUTH_WPA2_AES_PSK, 30000)) {
        printf("failed to connect to Wi-Fi.\n");
        exit(1);
    } 

    printf("Connected to the Wi-Fi.\n");
   

    create_rest_tasks();

#if 0
    cyw43_arch_lwip_begin();
#if CLIENT_TEST
    printf("\nReady, running iperf client\n");
    ip_addr_t clientaddr;
    ip4_addr_set_u32(&clientaddr, ipaddr_addr((IPERF_SERVER_IP)));
    //ip4_addr_set_u32(&clientaddr, ipaddr_addr(xstr(IPERF_SERVER_IP)));
    assert(lwiperf_start_tcp_client_default(&clientaddr, &iperf_report, NULL) != NULL);
#else
    printf("\nReady, running iperf server at %s\n", ip4addr_ntoa(netif_ip4_addr(netif_list)));
    lwiperf_start_tcp_server_default(&iperf_report, NULL);
#endif
    cyw43_arch_lwip_end();
#endif
    while(true) {
        // not much to do as LED is in another task, and we're using RAW (callback) lwIP API
        vTaskDelay(10000);
    }

    cyw43_arch_deinit();
}


int main( void )
{
    TaskHandle_t task;
    stdio_init_all();


    xTaskCreate(cy43_task, "CY43_Task", STACK_SIZE_CY43_TASK, NULL, PRIO_CY43_TASK, &task);

    vTaskStartScheduler();
    return 0;
}
