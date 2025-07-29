from .rest_fetcher import elec_fetch_loop
from .display_renderer import renderer_loop
from .local_comm import device_loop
from .log import Log
from . import config
import argparse

import threading
import sys
import time
from datetime import datetime
from queue import Queue


log_manager = Log() # This ensures the root logger is configured
logger = Log.get_logger(__name__)
Log().change_log_level(__name__, Log.DEBUG)



def parse_args():
    parser = argparse.ArgumentParser(description="Electricity Price Monitor")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--dump_img_buf", action="store_true", help="Save the image buuffers on file")
    parser.add_argument("--py-port", type=int, help="UDP port to listen on")
    parser.add_argument("--uc-port", type=int, help="UDP port uC is listening on")
    parser.add_argument("--uc-ip", type=str, help="IP of uC")
    return parser.parse_args()

def main():
    now = datetime.now()
    logger.debug(f"Started the main program at current time: {now}.")
    args = parse_args()
    config.update_from_args(args)

    logger.debug(f"{ config.DEBUG = }")
    logger.debug(f"{ config.DUMP_IMG_BUFF = }")
    logger.debug(f"{ config.PY_PORT = }")
    logger.debug(f"{ config.UC_PORT = }")

    elec_data_queue = Queue() #used for transfering data from rest_fetcher to display_renderer module,
    img_data_queue = Queue() #for transfering rendered image to the local server
    status_queue = Queue() # for transfering pico status to renderer
    stop_event = threading.Event() #kill signal

    threads = {
        "elec_fetch_loop": threading.Thread(target=elec_fetch_loop, args=(stop_event, elec_data_queue,), name="elec_fetch_loop"),
        "renderer_loop": threading.Thread(target=renderer_loop, args=(stop_event, elec_data_queue, status_queue, img_data_queue), name="renderer_loop"),
        "device_loop": threading.Thread(target=device_loop, args=(stop_event, status_queue, img_data_queue), name="device_loop"),
    }

    for t in threads.values():
        t.daemon = False
        t.start()

    try:
        while True:
            for name,t in threads.items():
                if not t.is_alive():
                    logger.error(f'thread {name} died, terminating')
                    stop_event.set()
                    for name, t in threads.items():
                        t.join(timeout=1.0)
                        logger.error(f'called join on thread {name}.')
                    logger.error(f'calling sys.exit in thread {name}.')
                    sys.exit(-1)

            time.sleep(2)

    except KeyboardInterrupt:
        logger.warning('Received keyboard interrupt, shutting down...')
        # Optional: Clean shutdown of threads
        stop_event.set()
        for name, t in threads.items():
            t.join(timeout=1.0)  # Give threads time to cleanup
            logger.error(f'called join on thread {name}.')
        logger.error(f'calling sys.exit in thread {name}.')
        sys.exit(0)

    except Exception as e:
        logger.warning(f'Interrupted:{e}')
        stop_event.set()
        for name, t in threads.items():
            t.join(timeout=1.0)  # Give threads time to cleanup
            logger.error(f'called join on thread {name}.')
        logger.error(f'calling sys.exit in thread {name}.')
        sys.exit(-2)        # try:
        #     main_loop()
        # except Exception as e:
        #     logger.error(f"[Exception raised in main_loop] {e}")
        #     break

if __name__ == "__main__":
    main()