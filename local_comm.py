from log import Log
from datetime import datetime, timedelta, timezone
import config
import socket
import time
import queue

logger = Log.get_logger(__name__)
Log().change_log_level(__name__, Log.DEBUG)
def start_lcl_server():
    logger.info("Started local server")


def get_device_status() ->dict:
    logger.debug("Getting device status")
    now = datetime.now()

    device = {
        'batt': 0,
        'date': now.strftime("%d-%m-%Y")
    }
    return device

def device_loop(stop_event, status_queue, img_data_queue):
    # Create UDP socket
    try:
        rcv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rcv_sock.bind(('0.0.0.0', config.PY_PORT))  # Listen on all interfaces
        rcv_sock.settimeout(1.0)  # Set timeout for receiving data

        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except Exception as e:
        logger.error(f'Failed to open/bind sockets: {e}. Terminating {__name__} thread')
        return


    while not stop_event.is_set():
        try:
            sleep_duration =10
            logger.debug(f'Going to sleep: {sleep_duration = }')
            for _ in range(
                    sleep_duration):  # this is very bad way of sleeping, sleep for a second and check if main called u to exit.
                time.sleep(1)
                if stop_event.is_set():
                    return
            pass
        except Exception as e:
            logger.error(f'Exception handled:{e}')

    logger.debug(f'Called to terminate, stopping thread {__name__}')