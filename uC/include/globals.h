#ifndef __GLOBALS_H
#define __GLOBALS_H

#include "FreeRTOS.h"
#include "semphr.h"

extern uint8_t reassembly_buff[MAX_DATA_BUFS][MAX_MSG_SIZE];
extern uint8_t disp_buf[DISP_BUFF_SIZE];
extern SemaphoreHandle_t g_wifi_ready_sem;
extern QueueHandle_t g_udp_epaper_queue;

#endif