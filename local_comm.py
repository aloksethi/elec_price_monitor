from log import Log
from datetime import datetime, timedelta, timezone

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