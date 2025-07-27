#include <string.h>
#include "FreeRTOS.h"
#include "task.h"
#include "event_groups.h"
#include "globals.h"
#include "config.h"
#include "epaper_driver.h"

//#define DISP_BUFF_SIZE	(648*480/8)
//uint8_t blk_buf[DISP_BUFF_SIZE];
//uint8_t red_buf[DISP_BUFF_SIZE];

void epaper_task(void *params) 
{
    //	memset(blk_buf, 0xffffffff, DISP_BUFF_SIZE/sizeof(uint32_t));
    //	memset(red_buf, 0xffffffff, DISP_BUFF_SIZE/sizeof(uint32_t));
    epaper_gpios_init();

    while (1) {
        // TODO: Wait for signal, decompress buffer, update display
        //        vTaskDelay(pdMS_TO_TICKS(2000));
        ulTaskNotifyTake( pdTRUE, portMAX_DELAY );
        UC_DEBUG("epaper started working\n");
        for (uint16_t i=0;i<DISP_BUFF_SIZE;i++)
        {
            bimg_buf[i] = ~bimg_buf[i];
            rimg_buf[i] = ~rimg_buf[i];
            //rimg_buf[i] &= ~bimg_buf[i];

        }
#if 1
        EPD_5IN83B_V2_Init();
        EPD_5IN83B_V2_Clear();

        DEV_Delay_ms(500);
        //EPD_5IN83B_V2_Display(bimg_buf, rimg_buf);

        EPD_5IN83B_V2_Display(rimg_buf, bimg_buf);
        DEV_Delay_ms(2000);
        EPD_5IN83B_V2_Sleep();
#endif


        xEventGroupSync(g_sleep_eg, SLEEP_EG_EPAPER_DONE_BIT, ALL_SYNC_BITS, portMAX_DELAY );
    }
}
