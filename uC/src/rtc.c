#include "pico/util/datetime.h"
#include "rtc.h"
#include "hardware/i2c.h"
#include "hardware/gpio.h"


static uint8_t conv_val_to_bcd(uint8_t val)
{
	uint8_t bcd = 0;

	if (val > 99)
		printf("error");

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
	uint8_t buf[3];  // two bytes of data and one register address
    int ret;

	buf[0] = EXT_RTC_MIN_REG;
	buf[1] = conv_val_to_bcd(t->min);
	buf[2] = conv_val_to_bcd(t->hour);
	ret = i2c_write_blocking(EXT_RTC_I2C_DEV, EXT_RTC_I2C_ADDRESS, &buf[0], 3, false);  
    if (ret == PICO_ERROR_GENERIC)
		printf("failed to wirite ext rtc\n");

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
		printf("failed to wirite ext rtc\n");
	
	ret = i2c_read_blocking(EXT_RTC_I2C_DEV, EXT_RTC_I2C_ADDRESS, &buf[0], 7, false);  // false - finished with bus
	if (ret == PICO_ERROR_GENERIC)
		printf("failed to read ext rtc\n");

	// hour is in reg 0x2
	hr = conv_bcd_to_val(buf[EXT_RTC_HR_REG]);
	printf("bcd Time:%02d:%02x:%02x  Day:%1d Date:%02x-%02x-20%02x\n",hr, buf[1], buf[0] , buf[3], buf[4], buf[5], buf[6]);

	t->year = 2000 + conv_bcd_to_val(buf[EXT_RTC_YR_REG]);  //device returns only last two digits of the year. not handling the rolloever to next centuary
	t->month = conv_bcd_to_val(buf[EXT_RTC_MON_REG]);
	t->day = conv_bcd_to_val(buf[EXT_RTC_DAY_REG]);
	t->dotw = conv_bcd_to_val(buf[EXT_RTC_DOW_REG]);
	t->hour = conv_bcd_to_val(buf[EXT_RTC_HR_REG]);
	t->min = conv_bcd_to_val(buf[EXT_RTC_MIN_REG]);
	t->sec = conv_bcd_to_val(buf[EXT_RTC_SEC_REG]);

	printf("Time:%02d:%02d:%02d  Day:%1d Date:%02d-%02d-%02d\n",t->hour, t->min, t->sec , t->dotw, t->day, t->month, t->year);
	return;
}