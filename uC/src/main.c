#include "pico/cyw43_arch.h"
#include "pico/stdlib.h"

#include "lwip/netif.h"
#include "lwip/ip4_addr.h"
#include "lwip/apps/lwiperf.h"

#include "FreeRTOS.h"
#include "task.h"
#include "config.h"

#include "pico/sleep.h"
#include "globals.h"
#include "rtc.h"

void udp_task(void *params);
void epaper_task(void *params);

#include "lwip/netif.h"
#include "lwip/ip_addr.h"
#include "lwip/init.h"

void print_ip_address() {
    struct netif *netif = netif_default;  // or netif_list

    //if (netif && !ip4_addr_isany_val(netif->ip_addr.u_addr.ip4)) {
    if (netif && !ip4_addr_isany_val(netif->ip_addr)) {
        printf("IP Address: %s\n", ip4addr_ntoa(&netif->ip_addr.addr));
    } else {
        printf("IP Address not assigned yet.\n");
    }
}

void create_rest_tasks(void)
{
    xTaskCreate(udp_task, "UDP_Task", STACK_SIZE_UDP_TASK, NULL, PRIO_UDP_TASK, &g_th_udp);
    xTaskCreate(epaper_task, "ePaper_Task", STACK_SIZE_EPAPER_TASK, NULL, PRIO_EPAPER_TASK, &g_th_epaper);

    return;	
}
//    TaskHandle_t cyw43_task; //no need of the task handle
void print_task_details() 
{
    TaskStatus_t *pxTaskStatusArray;
    UBaseType_t uxArraySize = uxTaskGetNumberOfTasks();

    pxTaskStatusArray = pvPortMalloc(uxArraySize * sizeof(TaskStatus_t));

    if (pxTaskStatusArray) {
        uxArraySize = uxTaskGetSystemState(
                pxTaskStatusArray,
                uxArraySize,
                NULL
                );

        for (UBaseType_t i = 0; i < uxArraySize; i++) {
            printf(
                    "Task: %s, Priority: %u, State: %u\n",
                    pxTaskStatusArray[i].pcTaskName,
                    pxTaskStatusArray[i].uxCurrentPriority,
                    pxTaskStatusArray[i].eCurrentState
                  );
        }

        vPortFree(pxTaskStatusArray);
    }
}
void sleep_fxn(void);
volatile uint8_t g_do_not_sleep = 1;
void cy43_task(__unused void *params) 
{
    static uint8_t onetime = 1;
    bool on = false;
    int ret;
    EventBits_t uxReturn;
    while (true)
    {
        if (cyw43_arch_init()) {
            printf("failed to initialise\n");
            vTaskDelay(pdMS_TO_TICKS(1000));
            continue;
            //           exit(1);
            //           return;
        }
        //cyw43_wifi_pm(&cyw43_state, CYW43_AGGRESSIVE_PM);
        cyw43_wifi_pm(&cyw43_state, CYW43_PERFORMANCE_PM);
        printf("arch init doen.\n");

        if (onetime)
        {
            create_rest_tasks();
            onetime = 0;
        }
        cyw43_arch_gpio_put(0, on);
        on = !on;

        cyw43_arch_enable_sta_mode();
        printf("Connecting to Wi-Fi...\n");
        //if (cyw43_arch_wifi_connect_timeout_ms(WIFI_SSID, WIFI_PASSWORD, CYW43_AUTH_WPA2_AES_PSK, 30000)) {
        if (cyw43_arch_wifi_connect_blocking(WIFI_SSID, WIFI_PASSWORD, CYW43_AUTH_WPA2_AES_PSK))
        {
            printf("failed to connect to Wi-Fi.\n");
            vTaskDelay(pdMS_TO_TICKS(1000));
            cyw43_arch_deinit();
            continue;
        } 

        ret = cyw43_tcpip_link_status (&cyw43_state, CYW43_ITF_STA);
        if (ret < 0)
            printf("error\n");
        else
            printf("ret is %d\n",ret);

        if (ret == CYW43_LINK_UP)
        {
            //vTaskDelay(pdMS_TO_TICKS(5000));
            print_ip_address();
            xSemaphoreGive(g_wifi_ready_sem);

        }

        printf("Connected to the Wi-Fi.\n");



        //    create_rest_tasks();
        // while(g_do_not_sleep)
        {
            vTaskDelay(100);
        }
        printf("time to sleep.\n");


        uxReturn = xEventGroupSync(
                g_sleep_eg,
                SLEEP_EG_CY43_DONE_BIT, //set this
                ALL_SYNC_BITS, // Wait for all
                portMAX_DELAY);

        if (( uxReturn & ALL_SYNC_BITS ) == ALL_SYNC_BITS) 
        {
            printf("CYW43: All tasks done. Going to sleep...\n");
            cyw43_arch_deinit(); //deinit the wifi to save power
                                 //print_task_details();
                                 //        g_do_not_sleep = 1;
            vTaskDelay(pdMS_TO_TICKS(10000));
            sleep_fxn();
        }
        else
        {
            printf("WTF: what do i do now:?\n");
        }
    }
}

void vApplicationStackOverflowHook( TaskHandle_t xTask, char *pcTaskName ) 
{
    printf("Stack overflow in task: %s\n", pcTaskName);
    for( ;; );
}

void sleep_fxn(void)
{
    printf("Switching to XOSC\n");
    uart_default_tx_wait_blocking();

    // Set the crystal oscillator as the dormant clock source, UART will be reconfigured from here
    // This is necessary before sending the pico into dormancy
    sleep_run_from_xosc();

    printf("Going dormant until GPIO %d goes edge high\n", PICO_WAKEUP_GPIO);
    uart_default_tx_wait_blocking();

    // Go to sleep until we see a high edge on GPIO 10
    sleep_goto_dormant_until_edge_high(PICO_WAKEUP_GPIO);

    // Re-enabling clock sources and generators.
    sleep_power_up();
    printf("awake now\n");
}

int main( void )
{
    TaskHandle_t task;
    stdio_init_all();
    g_wifi_ready_sem = xSemaphoreCreateBinary();
    if (g_wifi_ready_sem == NULL) 
    {
        printf("failed to create bin sem\n");
        return -1;
    }

    g_sleep_eg = xEventGroupCreate();
    if( g_sleep_eg == NULL )
    {
        printf("failed to create event group for sleeping\n");
        return -1;
    }
#if 0

    g_udp_epaper_sem = xSemaphoreCreateBinary();
    if (g_udp_epaper_sem == NULL) 
    {
        printf("failed to create bin sem\n");
        return -1;
    }
    g_udp_epaper_queue = xQueueCreate(MAX_UDP_EPAPER_QUEUE, sizeof(uint32_t));
    if (g_udp_epaper_queue == NULL)
    {
        printf("failed to create udp-epaper queue\n");
        return;
    }
#endif        
    xTaskCreate(cy43_task, "CY43_Task", STACK_SIZE_CY43_TASK, NULL, PRIO_CY43_TASK, &g_th_cyw43);


    vTaskStartScheduler();
    return 0;
}
