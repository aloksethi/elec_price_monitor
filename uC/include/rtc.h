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
#define EXT_RTC_POWER_PIN       (19)

/* DS3231 internal registers*/
#define EXT_RTC_SEC_REG         (0x0)
#define EXT_RTC_MIN_REG         (0x1)
#define EXT_RTC_HR_REG          (0x2)
#define EXT_RTC_DOW_REG         (0x3)
#define EXT_RTC_DAY_REG         (0x4)
#define EXT_RTC_MON_REG         (0x5)
#define EXT_RTC_YR_REG          (0x6)
#define EXT_RTC_A1_SEC_REG      (0x7)
#define EXT_RTC_A1_MIN_REG      (0x8)
#define EXT_RTC_A1_HR_REG       (0x9)
#define EXT_RTC_A1_DYDT_REG     (0xa)
#define EXT_RTC_CONTROL_REG     (0xe)

void ext_rtc_setup(void);
void ext_rtc_power_up(void);
void ext_rtc_power_down(void);
void ext_rtc_write_time(datetime_t *t);
void ext_rtc_read_time(datetime_t *t);
void ext_rtc_alarm_ack(void);
void ext_rtc_set_psec_alarm(void);
void ext_rtc_set_alarm(void);

void dbg_print_i2c();
#endif
