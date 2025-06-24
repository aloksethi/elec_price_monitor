from rest_fetcher import fetch_elec_data
from display_renderer import render_image
from local_comm import get_device_status
from log import Log
import config

import threading
import sys
import time
from datetime import datetime, timedelta
from queue import Queue

FETCH_INTERVAL = 60

logger = Log.get_logger("main")
Log().change_log_level("main", Log.WARNING)


def fix_elec_data(today_data, tmrw_data) -> tuple[dict, dict]:
    if (len(today_data) != 24) or (len(tmrw_data) != 24):
        logger.info(f'{len(today_data) =} {len(tmrw_data) =}')

    fxd_today_data = [{'date': '', 'hour': i, 'price': float('nan')} for i in range(24)]
    fxd_tmrw_data = [{'date': '', 'hour': i, 'price': float('nan')} for i in range(24)]

    numel = len(today_data)
    if (numel <= 2):# i don;t know how to deal if there are less than three elments in the array, assuming 0 will
        # contain data of yesterday and -1 will contain data of tmrw, so i will use 1 as data of today
        logger.error(f'numel is less than 2 {numel =}')

    ii = 0
    fxd_today_data[0]['date'] = today_data[0]['date']
    fxd_today_data[0]['hour'] = 0#today_data[0]['hour']
    fxd_today_data[0]['price'] = float('nan')#today_data[0]['price']

    fxd_tmrw_data[0]['date'] = today_data[-1]['date']
    fxd_tmrw_data[0]['hour'] = today_data[-1]['hour']
    fxd_tmrw_data[0]['price'] = today_data[-1]['price']
    ii = 0
    for i in range(1, 24):
        fxd_today_data[i]['date'] = today_data[0]['date']
        fxd_today_data[i]['hour'] = (i)
        if (int(today_data[ii]['hour']) == i):
            fxd_today_data[i]['price'] = today_data[ii]['price']
            ii = ii + 1
        else:
            fxd_today_data[i]['price'] = fxd_today_data[i-1]['price']

    return fxd_today_data, fxd_tmrw_data
def elec_fetch_loop():
    while True:
        now = datetime.now()
        logger.debug(f'in main loop {now}')
        try:
            today_data = fetch_elec_data(now)
            tmrw_data = fetch_elec_data(now + timedelta(days=1))

            if not today_data:
                # if  today_data is not available then do not call fix_elec_data
                logger.error(f'No data for today')
                sleep_duration = config.SLEEP_DUR_NO_DATA
            elif not tmrw_data:
                logger.warning(f'No data for tmrw')
                sleep_duration = config.SLEEP_DUR_NO_TMRW_DATA
                fxd_today_data, fxd_tmrw_data = fix_elec_data(today_data, tmrw_data)
            else:
                logger.debug(f'Data available for today and tmrw')
                sleep_duration = config.SLEEP_DUR_DATA_AVLBL
                fxd_today_data, fxd_tmrw_data = fix_elec_data(today_data, tmrw_data)

        except Exception as e:
            logger.error(f'Exception in elec_fetch_loop: {e}')
            sleep_duration = config.SLEEP_DUR_NO_DATA


        logger.debug(f'Going to sleep: {sleep_duration = }')
        if not config.DEBUG:
            time.sleep(sleep_duration)


def main_loop():
    now = datetime.now()
    logger.debug(f"Current time: {now}")

#make sure the loop runs whenever the hour changes




    device = get_device_status()
    #
    # two issues, first the data maynot have 24 enteries even for a day as the api will return no data for an hour if
    # the price is exactly the same as previos price. second issue is the last entry is for 00 hr of the next day so it should be treated like that

    img = render_image(device, fxd_today_data, fxd_today_data, now)
    img.save('test3.png')
    # raise Exception("testing")
"""
    print("[INFO] Updating display...")



time.sleep(FETCH_INTERVAL)
"""

if __name__ == "__main__":

    threads = {
        "elec_fetch_loop": threading.Thread(target=elec_fetch_loop, name="elec_fetch_loop"),
    }

    for t in threads.values():
        t.daemon = False
        t.start()

    try:
        while True:
            for name,t in threads.items():
                if not t.is_alive():
                    logger.error(f'thread {name} died, terminating')
                    sys.exit(-1)

            time.sleep(2)

    except Exception as e:
        logger.warning(f'Interrupted:{e}')
        sys.exit(0)
        # try:
        #     main_loop()
        # except Exception as e:
        #     logger.error(f"[Exception raised in main_loop] {e}")
        #     break
