#ifndef __GLOBALS_H
#define __GLOBALS_H

#include "FreeRTOS.h"
#include "semphr.h"
#include "event_groups.h"
#include "config.h"

extern uint8_t reassembly_buff[MAX_DATA_BUFS][MAX_MSG_SIZE];
extern uint8_t rimg_buf[DISP_BUFF_SIZE];
extern uint8_t bimg_buf[DISP_BUFF_SIZE];
extern SemaphoreHandle_t g_wifi_ready_sem;
//extern QueueHandle_t g_udp_epaper_queue;
//extern SemaphoreHandle_t g_udp_epaper_sem;

extern TaskHandle_t g_th_cyw43;
extern TaskHandle_t g_th_udp;  
extern TaskHandle_t g_th_epaper;

extern EventGroupHandle_t g_sleep_eg;

#define SLEEP_EG_UDP_DONE_BIT       (1 << 0)
#define SLEEP_EG_EPAPER_DONE_BIT    (1 << 1)
#define SLEEP_EG_CY43_DONE_BIT      (1 << 2)
#define ALL_SYNC_BITS ( SLEEP_EG_UDP_DONE_BIT | SLEEP_EG_EPAPER_DONE_BIT | SLEEP_EG_CY43_DONE_BIT )

#endif
