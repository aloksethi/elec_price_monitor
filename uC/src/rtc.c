#include <stdio.h>
#include "pico/util/datetime.h"
#include "rtc.h"
#include "hardware/i2c.h"
#include "hardware/gpio.h"
#include "config.h"

static uint8_t conv_val_to_bcd(uint8_t val)
{
	uint8_t bcd = 0;

	if (val > 99)
		UC_ERROR(("val incorrect, should be <99\n"));

	bcd = ((uint8_t)(val / 10))<< 4;
	bcd |= ((uint8_t)(val % 10));
	
	return bcd;
}

static uint8_t conv_bcd_to_val(uint8_t code)
{
	uint8_t val = 0;

	val = ((code & 0xf0)>>4)*10 + ((code & 0x0f));
	
	return val;
}

void setup_ext_rtc() 
{
    gpio_init(EXT_RTC_I2C_SDA_PIN);
    gpio_set_function(EXT_RTC_I2C_SDA_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(EXT_RTC_I2C_SDA_PIN);

    gpio_init(EXT_RTC_I2C_SCL_PIN);
    gpio_set_function(EXT_RTC_I2C_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(EXT_RTC_I2C_SCL_PIN);

    i2c_init(EXT_RTC_I2C_DEV, EXT_RTC_I2C_BAUDRATE);

	return;
}

void write_ext_rtc(datetime_t *t)
{
	// lets write only the hours and mins
	uint8_t buf[8];  // two bytes of data and one register address
    int ret;

	buf[0] = EXT_RTC_SEC_REG;//EXT_RTC_MIN_REG;
	buf[1] = conv_val_to_bcd(t->sec);
    buf[2] = conv_val_to_bcd(t->min);
	buf[3] = conv_val_to_bcd(t->hour);
    buf[4] = conv_val_to_bcd(0);
    buf[5] = conv_val_to_bcd(t->day);
    buf[6] = conv_val_to_bcd(t->month);
    buf[7] = conv_val_to_bcd(t->year - 2000);
	ret = i2c_write_blocking(EXT_RTC_I2C_DEV, EXT_RTC_I2C_ADDRESS, &buf[0], 8, false);  
    if (ret == PICO_ERROR_GENERIC)
		UC_ERROR(("failed to wirite ext rtc\n"));

}

void read_ext_rtc(datetime_t *t)
{
 	uint8_t buf[7];
    uint8_t reg = EXT_RTC_SEC_REG;
	int ret;
	//uint8_t data;
	uint8_t hr;

	/* in DS3231, time registers start from 0 to 0x6, so need to read only 7 uint8s from the i2c*/
	assert(EXT_RTC_YR_REG < 7);

    ret = i2c_write_blocking(EXT_RTC_I2C_DEV, EXT_RTC_I2C_ADDRESS, &reg, 1, true);  // true to keep master control of bus
    if (ret == PICO_ERROR_GENERIC)
		UC_ERROR(("failed to wirite ext rtc\n"));
	
	ret = i2c_read_blocking(EXT_RTC_I2C_DEV, EXT_RTC_I2C_ADDRESS, &buf[0], 7, false);  // false - finished with bus
	if (ret == PICO_ERROR_GENERIC)
		UC_ERROR(("failed to read ext rtc\n"));

	// hour is in reg 0x2
	hr = conv_bcd_to_val(buf[EXT_RTC_HR_REG]);
	//printf("bcd Time:%02d:%02x:%02x  Day:%1d Date:%02x-%02x-20%02x\n",hr, buf[1], buf[0] , buf[3], buf[4], buf[5], buf[6]);

	t->year = 2000 + conv_bcd_to_val(buf[EXT_RTC_YR_REG]);  //device returns only last two digits of the year. not handling the rolloever to next centuary
	t->month = conv_bcd_to_val(buf[EXT_RTC_MON_REG]);
	t->day = conv_bcd_to_val(buf[EXT_RTC_DAY_REG]);
	t->dotw = conv_bcd_to_val(buf[EXT_RTC_DOW_REG]);
	t->hour = conv_bcd_to_val(buf[EXT_RTC_HR_REG]);
	t->min = conv_bcd_to_val(buf[EXT_RTC_MIN_REG]);
	t->sec = conv_bcd_to_val(buf[EXT_RTC_SEC_REG]);

	//printf("Time:%02d:%02d:%02d  Day:%1d Date:%02d-%02d-%02d\n",t->hour, t->min, t->sec , t->dotw, t->day, t->month, t->year);
	return;
}

// Following functions are taken from rpi pico i2c documentation
// I2C reserves some addresses for special purposes. We exclude these from the scan.
// These are any addresses of the form 000 0xxx or 111 1xxx
static bool reserved_addr(uint8_t addr) {
    return (addr & 0x78) == 0 || (addr & 0x78) == 0x78;
}
void dbg_print_i2c()
{

    for (int addr = 0; addr < (1 << 7); ++addr) {
        if (addr % 16 == 0) {
            UC_DEBUG(("%02x ", addr));
        }

        // Perform a 1-byte dummy read from the probe address. If a slave
        // acknowledges this address, the function returns the number of bytes
        // transferred. If the address byte is ignored, the function returns
        // -1.

        // Skip over any reserved addresses.
        int ret;
        uint8_t rxdata;
        if (reserved_addr(addr))
            ret = PICO_ERROR_GENERIC;
        else
            ret = i2c_read_blocking(EXT_RTC_I2C_DEV, addr, &rxdata, 1, false);

        UC_DEBUG((ret < 0 ? "." : "@"));
        UC_DEBUG((addr % 16 == 15 ? "\n" : "  "));
    }
    return;
}