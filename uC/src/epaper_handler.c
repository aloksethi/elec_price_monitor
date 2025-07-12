#include <string.h>
#include "FreeRTOS.h"
#include "task.h"
#define DISP_BUFF_SIZE	(648*480/8)
//uint8_t blk_buf[DISP_BUFF_SIZE];
//uint8_t red_buf[DISP_BUFF_SIZE];

void epaper_task(void *params) 
{
//	memset(blk_buf, 0xffffffff, DISP_BUFF_SIZE/sizeof(uint32_t));
//	memset(red_buf, 0xffffffff, DISP_BUFF_SIZE/sizeof(uint32_t));
    while (1) {
        // TODO: Wait for signal, decompress buffer, update display
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}
