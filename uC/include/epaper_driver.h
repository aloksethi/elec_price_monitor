#ifndef __EPAPER_DRIVER_H
#define __EPAPER_DRIVER_H

    #define EPD_RST_PIN     12
	#define EPD_DC_PIN      8
	#define EPD_BUSY_PIN    13
	#define EPD_CS_PIN      9
	#define EPD_CLK_PIN		10
	#define EPD_MOSI_PIN	11


	#define SPI_PORT spi1

	#define EPD_5IN83B_V2_WIDTH       648
	#define EPD_5IN83B_V2_HEIGHT      480

	#define UBYTE   uint8_t
#define UWORD   uint16_t
#define UDOUBLE uint32_t


void epaper_gpios_init(void);
void DEV_Delay_ms(UDOUBLE xms);
UBYTE EPD_5IN83B_V2_Init(void);
void EPD_5IN83B_V2_TurnOnDisplay(void);
void EPD_5IN83B_V2_Clear(void);
void EPD_5IN83B_V2_Display(const UBYTE *blackimage, const UBYTE *ryimage);
void EPD_5IN83B_V2_Sleep(void);



#endif