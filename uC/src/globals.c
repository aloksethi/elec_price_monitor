#include "config.h"
#include "globals.h"
#include "FreeRTOS.h"
#include "event_groups.h"

uint8_t reassembly_buff[MAX_DATA_BUFS][MAX_MSG_SIZE];
// seems that i do ahve space for two image buffers, so in order to avoid situations 
// where have got one color data but the other one is not available, n i have
// to wait for other data, decided to use two buffers. if in future there is no
// RAM avaialble, move to one buffer
uint8_t rimg_buf[DISP_BUFF_SIZE]; 
uint8_t bimg_buf[DISP_BUFF_SIZE];


SemaphoreHandle_t g_wifi_ready_sem;
//QueueHandle_t g_udp_epaper_queue;
//SemaphoreHandle_t g_udp_epaper_sem;

EventGroupHandle_t g_sleep_eg;

TaskHandle_t g_th_cyw43 = NULL;
TaskHandle_t g_th_udp = NULL;  
TaskHandle_t g_th_epaper = NULL;