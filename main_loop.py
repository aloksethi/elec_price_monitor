from rest_fetcher import elec_fetch_loop
from display_renderer import renderer_loop
from local_comm import get_device_status
from log import Log
import config

import threading
import sys
import time
from datetime import datetime, timedelta, time as dt_time
from queue import Queue

FETCH_INTERVAL = 60

logger = Log.get_logger(__name__)
Log().change_log_level(__name__, Log.DEBUG)



# def main_loop():
#     now = datetime.now()
#     logger.debug(f"Current time: {now}")
#
# #make sure the loop runs whenever the hour changes
#
#
#
#
#     device = get_device_status()
#     #
#     # two issues, first the data maynot have 24 enteries even for a day as the api will return no data for an hour if
#     # the price is exactly the same as previos price. second issue is the last entry is for 00 hr of the next day so it should be treated like that
#
#     img = render_image(device, fxd_today_data, fxd_today_data, now)
#     img.save('test3.png')
#     # raise Exception("testing")
"""
    print("[INFO] Updating display...")



time.sleep(FETCH_INTERVAL)
"""

if __name__ == "__main__":
    now = datetime.now()
    logger.debug(f"Started the main program at current time: {now}.")

    elec_data_queue = Queue() #used for transfering data from rest_fetcher to display_renderer module,
    img_data_queue = Queue() #for transfering rendered image to the local server
    status_queue = Queue() # for transfering pico status to renderer
    threads = {
        "elec_fetch_loop": threading.Thread(target=elec_fetch_loop, args=(elec_data_queue,), name="elec_fetch_loop"),
        "renderer_loop": threading.Thread(target=renderer_loop, args=(elec_data_queue, status_queue, img_data_queue), name="renderer_loop"),
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
