#include "globals.h"
#include "config.h"
#include "epaper_driver.h"
#include "hardware/gpio.h"
#include "hardware/spi.h"


void epaper_gpios_init(void)
{
    gpio_init (EPD_RST_PIN);
	gpio_set_dir(EPD_RST_PIN, GPIO_OUT);


    gpio_init (EPD_DC_PIN);
	gpio_set_dir(EPD_DC_PIN, GPIO_OUT);

    gpio_init (EPD_CS_PIN);
	gpio_set_dir(EPD_CS_PIN, GPIO_OUT);

    gpio_init (EPD_BUSY_PIN);
	gpio_set_dir(EPD_BUSY_PIN, GPIO_IN);

   gpio_put(EPD_CS_PIN, 1);


    spi_init(SPI_PORT, 4000 * 1000);
    gpio_set_function(EPD_CLK_PIN, GPIO_OUT);
    gpio_set_function(EPD_MOSI_PIN, GPIO_OUT);
}

void DEV_Digital_Write(UWORD Pin, UBYTE Value)
{
	gpio_put(Pin, Value);
}
UBYTE DEV_Digital_Read(UWORD Pin)
{
	return gpio_get(Pin);
}
void DEV_Delay_ms(UDOUBLE xms)
{
    vTaskDelay(pdMS_TO_TICKS(xms));
}

void DEV_SPI_WriteByte(uint8_t Value)
{
    spi_write_blocking(SPI_PORT, &Value, 1);
}

static void EPD_5IN83B_V2_SendCommand(UBYTE Reg)
{
    DEV_Digital_Write(EPD_DC_PIN, 0);
    DEV_Digital_Write(EPD_CS_PIN, 0);
    DEV_SPI_WriteByte(Reg);
    DEV_Digital_Write(EPD_CS_PIN, 1);
}

static void EPD_5IN83B_V2_SendData(UBYTE Data)
{
    
    DEV_Digital_Write(EPD_CS_PIN, 0);
    DEV_Digital_Write(EPD_DC_PIN, 1);
    DEV_SPI_WriteByte(Data);
    DEV_Digital_Write(EPD_CS_PIN, 1);
}

void EPD_5IN83B_V2_WaitUntilIdle(void)
{
    printf("e-Paper busy\r\n");
	UBYTE busy;
	do
	{
		EPD_5IN83B_V2_SendCommand(0x71);
		busy = DEV_Digital_Read(EPD_BUSY_PIN);
		busy =!(busy & 0x01);
	}
	while(busy);   
	DEV_Delay_ms(200);     
    printf("e-Paper busy release\r\n");
}


static void EPD_5IN83B_V2_Reset(void)
{
    DEV_Digital_Write(EPD_RST_PIN, 1);
    DEV_Delay_ms(200);
    DEV_Digital_Write(EPD_RST_PIN, 0);
    DEV_Delay_ms(2);
    DEV_Digital_Write(EPD_RST_PIN, 1);
    DEV_Delay_ms(200);
}


UBYTE EPD_5IN83B_V2_Init(void)
{
    EPD_5IN83B_V2_Reset();

	EPD_5IN83B_V2_SendCommand(0x01);			//POWER SETTING
	EPD_5IN83B_V2_SendData (0x07);
	EPD_5IN83B_V2_SendData (0x07);    //VGH=20V,VGL=-20V
	EPD_5IN83B_V2_SendData (0x3f);		//VDH=15V
	EPD_5IN83B_V2_SendData (0x3f);		//VDL=-15V

	EPD_5IN83B_V2_SendCommand(0x04); //POWER ON
	DEV_Delay_ms(100);  
	EPD_5IN83B_V2_WaitUntilIdle();        //waiting for the electronic paper IC to release the idle signal

	EPD_5IN83B_V2_SendCommand(0X00);			//PANNEL SETTING
	EPD_5IN83B_V2_SendData(0x0F);   //KW-3f   KWR-2F	BWROTP 0f	BWOTP 1f

	EPD_5IN83B_V2_SendCommand(0x61);        	//tres			
	EPD_5IN83B_V2_SendData (0x02);		//source 648
	EPD_5IN83B_V2_SendData (0x88);
	EPD_5IN83B_V2_SendData (0x01);		//gate 480
	EPD_5IN83B_V2_SendData (0xe0);

	EPD_5IN83B_V2_SendCommand(0X15);		
	EPD_5IN83B_V2_SendData(0x00);		

	EPD_5IN83B_V2_SendCommand(0X50);			//VCOM AND DATA INTERVAL SETTING
	EPD_5IN83B_V2_SendData(0x11);
	EPD_5IN83B_V2_SendData(0x07);

	EPD_5IN83B_V2_SendCommand(0X60);			//TCON SETTING
	EPD_5IN83B_V2_SendData(0x22);
		
    return 0;
}

void EPD_5IN83B_V2_TurnOnDisplay(void)
{
	EPD_5IN83B_V2_SendCommand(0x12);			//DISPLAY REFRESH 	
	DEV_Delay_ms(100);	        //!!!The delay here is necessary, 200uS at least!!!     
	EPD_5IN83B_V2_WaitUntilIdle();        //waiting for the electronic paper IC to release the idle signal
}


void EPD_5IN83B_V2_Clear(void)
{
    UWORD Width, Height;
    Width =(EPD_5IN83B_V2_WIDTH % 8 == 0)?(EPD_5IN83B_V2_WIDTH / 8 ):(EPD_5IN83B_V2_WIDTH / 8 + 1);
    Height = EPD_5IN83B_V2_HEIGHT;
    UWORD i;
    EPD_5IN83B_V2_SendCommand(0x10);
    for(i=0; i<Width*Height; i++) {
        EPD_5IN83B_V2_SendData(0xff);

    }
    EPD_5IN83B_V2_SendCommand(0x13);
    for(i=0; i<Width*Height; i++)	{
        EPD_5IN83B_V2_SendData(0x00);

    }
    EPD_5IN83B_V2_TurnOnDisplay();
}

void EPD_5IN83B_V2_Display(const UBYTE *blackimage, const UBYTE *ryimage)
{
    UDOUBLE Width, Height;
    Width =(EPD_5IN83B_V2_WIDTH % 8 == 0)?(EPD_5IN83B_V2_WIDTH / 8 ):(EPD_5IN83B_V2_WIDTH / 8 + 1);
    Height = EPD_5IN83B_V2_HEIGHT;
	//send black data
    if  (blackimage != NULL)
    {
        EPD_5IN83B_V2_SendCommand(0x10);
        for (UDOUBLE j = 0; j < Height; j++) {
            for (UDOUBLE i = 0; i < Width; i++) {
                EPD_5IN83B_V2_SendData(blackimage[i + j * Width]);
            }
        }
    }

    //send red data
    if  (ryimage != NULL)
    {
        EPD_5IN83B_V2_SendCommand(0x13);
        for (UDOUBLE j = 0; j < Height; j++) {
            for (UDOUBLE i = 0; i < Width; i++) {
                EPD_5IN83B_V2_SendData(~ryimage[i + j * Width]);
            }
        }
    }
    EPD_5IN83B_V2_TurnOnDisplay();
}

void EPD_5IN83B_V2_Sleep(void)
{
	EPD_5IN83B_V2_SendCommand(0X02);  	//power off
	EPD_5IN83B_V2_WaitUntilIdle();        //waiting for the electronic paper IC to release the idle signal
	EPD_5IN83B_V2_SendCommand(0X07);  	//deep sleep
	EPD_5IN83B_V2_SendData(0xA5);
}

