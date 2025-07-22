#ifndef __RTC_H
#define __RTC_H

#include "hardware/i2c.h"
#include "hardware/gpio.h"

/* external RTC connections*/
#define EXT_RTC_I2C_DEV         (i2c0)
#define EXT_RTC_I2C_ADDRESS     (0x68)/*(0x68)*/
#define EXT_RTC_I2C_BAUDRATE    (100000)
#define EXT_RTC_I2C_SDA_PIN     (16)
#define EXT_RTC_I2C_SCL_PIN     (17)

/* DS3231 internal registers*/
#define EXT_RTC_SEC_REG         (0x0)
#define EXT_RTC_MIN_REG         (0x1)
#define EXT_RTC_HR_REG          (0x2)
#define EXT_RTC_DOW_REG         (0x3)
#define EXT_RTC_DAY_REG         (0x4)
#define EXT_RTC_MON_REG         (0x5)
#define EXT_RTC_YR_REG          (0x6)


void write_ext_rtc(datetime_t *t);
void read_ext_rtc(datetime_t *t);
void setup_ext_rtc();

#endif
