from log import Log
import config
import requests
import os
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
import time



logger = Log.get_logger(__name__)
Log().change_log_level(__name__, Log.WARNING)


def utc_time_to_local(utc_time:str) -> datetime:
    utc_datetime = datetime.strptime(utc_time, "%Y-%m-%dT%H:%MZ")
    utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    local_time = utc_datetime.astimezone()
    logger.debug(f"utc time {utc_datetime}")
    logger.debug(f"local_time: {local_time}")
    return local_time

def parse_xml(xml_data:str):
    ns = {'ns': 'urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3'}

    try:
        logger.debug("Parsing XML data")
        root = ET.fromstring(xml_data)

        # Extract time interval
        period_start_str = root.find('.//ns:period.timeInterval/ns:start', ns).text
        period_end_str = root.find('.//ns:period.timeInterval/ns:end', ns).text

        period_start = utc_time_to_local(period_start_str)
        period_end = utc_time_to_local(period_end_str)

        logger.info(f"Period start (local): {period_start_str}")
        logger.info(f"Period end   (local): {period_end_str}")

        timeseries = root.find('ns:TimeSeries', ns)
        if timeseries is None:
            logger.error("No <TimeSeries> element found in XML")
            raise ValueError("No <TimeSeries> element found in XML")

        period = timeseries.find('ns:Period', ns)
        if period is None:
            logger.error("No <Period> element found in <TimeSeries>")
            raise ValueError("No <Period> element found in <TimeSeries>")

        resolution = period.find('ns:resolution', ns)
        if resolution is None:
            logger.error("No <resolution> element found in <Period>")
            raise ValueError("No <Resolution> element found in <Period>")

        resolution_text = resolution.text
        logger.debug(f"Resolution found: {resolution_text}")

        if resolution_text == 'PT60M':
            time_mult = 60
        else:
            time_mult = 15

        # Step 5: Extract the <Point> entries inside the <Period>
        points = period.findall('ns:Point', ns)
        logger.debug(f"Found {len(points)} <Point> entries")

        # Step 6: Parse each <Point> and collect as a list of dicts
        data = []
        for point in points:
            position = point.find('ns:position', ns)
            price = point.find('ns:price.amount', ns)

            # Safety check for missing data
            if position is None or price is None:
                logger.warning("Missing <position> or <price.amount> in <Point>")
                continue

            time_delta = time_mult * (int(position.text) - 1)
            pos_time = period_start + timedelta(minutes=time_delta)

            #print(f"start time:{period_start} position:{position.text} pos_time:{pos_time}")
            #print(f"hour: {pos_time.hour} price:{price.text}")
            # Store as Python-native types
            data.append({
                'date': pos_time.strftime("%d-%m-%Y"),
                'hour': pos_time.strftime("%H"),
                'price': round(float(price.text)/10, 3) #converting from e/MWh to c/KWh
            })
        logger.debug(f"{data}")
        logger.info(f"Parsed {len(data)} data points from XML")
        return data
    except Exception as e:  #ET.ParseError
        logger.error(f"XML parsing error: {e}")
        logger.debug(f"Check if reason was returned")
        try:
            ns = {'ns': 'urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0'}
            reason = root.find('.//ns:Reason/ns:text', ns).text
            logger.debug(f"Reason found: {reason}")
        except Exception as e:
            logger.error(f"Didn't find the reason either: {e}")
            logger.debug("dumping the xml file")
            logger.debug(f"{xml_data}")
    raise
    # except Exception as e:
    #     logger.error(f"Unexpected error while parsing XML: {e}")
    #     raise

def fetch_elec_data(dt:datetime) ->dict:
    api_token = os.environ.get("API_TOKEN")
    if  not api_token:
        logger.error("Missing API_TOKEN environment variable")
        raise ValueError("Missing API_TOKEN environment variable")

    start_dt = dt.replace(hour=0, minute=0)
    end_dt = dt.replace(hour=1, minute=0)

    params = {
        "securityToken": api_token,
        "in_Domain": "10YFI-1--------U",
        "out_Domain": "10YFI-1--------U",
        "periodStart": start_dt.strftime("%Y%m%d%H%M"),
        "periodEnd": end_dt.strftime("%Y%m%d%H%M"),
        "documentType": "A44",
    }
    safe_params = params.copy()
    safe_params["securityToken"] = "*****"

    logger.debug(f"Fetching data with parameters: {safe_params}")
    try:
        response = requests.get(config.BASE_URL, params=params)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch API data: {e}")

    # data = response.text
    try:
        data = parse_xml(response.text)
    except:
        data = []
        #print(data)

    return data


def fix_elec_data(today_data, tmrw_data) -> tuple[dict, dict]:
    if (len(today_data) != 24) or (len(tmrw_data) != 24):
        logger.info(f'{len(today_data) =} {len(tmrw_data) =}')

    fxd_today_data = [{'date': '', 'hour': i, 'price': float('nan')} for i in range(24)]
    fxd_tmrw_data = [{'date': '', 'hour': i, 'price': float('nan')} for i in range(24)]

    # this part is probably not needed.
    numel = len(today_data)
    if (numel <= 2):# i don;t know how to deal if there are less than three elments in the array, assuming 0 will
        # contain data of yesterday and -1 will contain data of tmrw, so i will use 1 as data of today
        logger.error(f'numel is less than 2 {numel =}')

    # do the fix only if there is no hour=0 entry in today data
    if (int(today_data[0]['hour']) == 0):
        fxd_today_data[0]['price'] = today_data[0]['price']
    else:
        fxd_today_data[0]['price'] = float('nan')

    fxd_today_data[0]['date'] = today_data[0]['date']
    fxd_today_data[0]['hour'] = 0  # today_data[0]['hour']

    fxd_tmrw_data[0]['date'] = today_data[-1]['date']
    fxd_tmrw_data[0]['hour'] = int(today_data[-1]['hour'])
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

    ii = 0
    for i in range(1, 24):
        fxd_tmrw_data[i]['date'] = tmrw_data[0]['date']
        fxd_tmrw_data[i]['hour'] = (i)
        if (int(tmrw_data[ii]['hour']) == i):
            fxd_tmrw_data[i]['price'] = tmrw_data[ii]['price']
            ii = ii + 1
        else:
            fxd_tmrw_data[i]['price'] = fxd_tmrw_data[i - 1]['price']

    return fxd_today_data, fxd_tmrw_data
def elec_fetch_loop(stop_event, queue_out):
    today_data = []
    tmrw_data = []

    last_sent_data = None
    last_fetch_date = None

    while not stop_event.is_set():
        try:
            now = datetime.now()
            today_str = now.strftime('%d.%m.%Y')
            logger.debug(f'In elec_fetch_loop: {now}.')

            # today_data = fetch_elec_data(now)
            # tmrw_data = fetch_elec_data(now + timedelta(days=1))

            # Detect date change and rotate data
            if last_fetch_date and today_str != last_fetch_date:
                today_data = tmrw_data
                tmrw_data = []
                last_fetch_date = today_str
                logger.info("Date changed — shifted tmrw_data to today_data.")

            if not today_data:
                fetched_tday = fetch_elec_data(now)
                if fetched_tday:
                    today_data = fetched_tday
                    last_fetch_date = today_str
                    logger.debug("Fetched todays data")
                # else:
                #     # if  today_data is not available then do not call fix_elec_data
                #     logger.error(f'No data for today')
                #     current_data, next_data = False, False
                #     sleep_duration = config.SLEEP_DUR_NO_DATA

            if today_data and now.hour >= 12 and not tmrw_data:
                next_day = now + timedelta(days=1)
                fetched_tmrw = fetch_elec_data(next_day)
                if fetched_tmrw:
                    tmrw_data = fetched_tmrw
                    logger.debug("Fetched tmrw data")
            #         else:
            #             logger.warning(f'No data for tmrw')
            #             sleep_duration = config.SLEEP_DUR_NO_TMRW_DATA
            #             current_data, next_data = True, False
            #     fxd_today_data, fxd_tmrw_data = fix_elec_data(today_data, tmrw_data)
            # else:
            #     logger.debug(f'Data available for today and tmrw')
            #     sleep_duration = config.SLEEP_DUR_DATA_AVLBL
            #     current_data, next_data = True, True
            #     fxd_today_data, fxd_tmrw_data = fix_elec_data(today_data, tmrw_data)


            if today_data:
                # If today’s data is valid, fix and send even if tmrw_data is not present
                fxd_today_data, fxd_tmrw_data = fix_elec_data(today_data, tmrw_data)
                data_bundle = {
                    'today': fxd_today_data,
                    'tmrw': fxd_tmrw_data
                }
                if data_bundle != last_sent_data:
                    queue_out.put(data_bundle)
                    last_sent_data = data_bundle
                    logger.info("Sent fixed data to renderer.")

            # Decide sleep interval
            if today_data and tmrw_data:
                sleep_duration = config.SLEEP_DUR_DATA_AVLBL
            elif today_data:
                sleep_duration = config.SLEEP_DUR_NO_TMRW_DATA
            else:
                sleep_duration = config.SLEEP_DUR_NO_DATA

        except Exception as e:
            logger.error(f'Exception in elec_fetch_loop: {e}')
            if isinstance(e, ValueError):
                logger.error(f'Cannot return from this. bye.')
                return
            sleep_duration = config.SLEEP_DUR_NO_DATA

        logger.debug(f'Going to sleep: {sleep_duration = }')
        for _ in range(sleep_duration):  # this is very bad way of sleeping, sleep for a second and check if main called u to exit.
            time.sleep(1)
            if stop_event.is_set():
                return
        # time.sleep(sleep_duration)
