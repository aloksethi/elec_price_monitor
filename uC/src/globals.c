#include "config.h"
#include "globals.h"


uint8_t reassembly_buff[MAX_DATA_BUFS][MAX_MSG_SIZE];
uint8_t disp_buf[DISP_BUFF_SIZE];


SemaphoreHandle_t g_wifi_ready_sem;
QueueHandle_t g_udp_epaper_queue;
