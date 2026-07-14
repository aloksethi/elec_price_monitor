from elec_price_monitor.log import Log
from elec_price_monitor import config
import requests
import os
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
import time
from statistics import mean
#import pdb


logger = Log.get_logger(__name__)
Log().change_log_level(__name__, Log.WARNING)

PUB_NS = {'ns': 'urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3'}
ACK_NS = {'ns': 'urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0'}


def empty_day_data(date_str=''):
    return [{'date': date_str, 'hour': i, 'price': float('nan')} for i in range(24)]


def utc_time_to_local(utc_time:str) -> datetime:
    # TODO: fix it for dST.
    utc_datetime = datetime.strptime(utc_time, "%Y-%m-%dT%H:%MZ")
    utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    local_time = utc_datetime.astimezone()
    logger.debug(f"utc time {utc_datetime}")
    logger.debug(f"local_time: {local_time}")
    return local_time

def parse_xml(xml_data:str):
    try:
        logger.debug("Parsing XML data")
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
        return []

    reason_elem = root.find('.//ns:Reason/ns:text', ACK_NS)
    if reason_elem is not None and reason_elem.text:
        logger.warning(f"ENTSO-E acknowledgement: {reason_elem.text.strip()}")
        return []

    period_start_elem = root.find('.//ns:period.timeInterval/ns:start', PUB_NS)
    period_end_elem = root.find('.//ns:period.timeInterval/ns:end', PUB_NS)
    if (period_start_elem is None or period_end_elem is None
            or not period_start_elem.text or not period_end_elem.text):
        logger.warning("No period.timeInterval found in XML response")
        return []

    try:
        period_start_str = period_start_elem.text
        period_end_str = period_end_elem.text

        period_start = utc_time_to_local(period_start_str)
        period_end = utc_time_to_local(period_end_str)

        logger.info(f"Period start (local): {period_start_str}")
        logger.info(f"Period end   (local): {period_end_str}")

        timeseries = root.find('ns:TimeSeries', PUB_NS)
        if timeseries is None:
            logger.error("No <TimeSeries> element found in XML")
            return []

        period = timeseries.find('ns:Period', PUB_NS)
        if period is None:
            logger.error("No <Period> element found in <TimeSeries>")
            return []

        resolution = period.find('ns:resolution', PUB_NS)
        if resolution is None or not resolution.text:
            logger.error("No <resolution> element found in <Period>")
            return []

        resolution_text = resolution.text
        logger.debug(f"Resolution found: {resolution_text}")

        if resolution_text == 'PT60M':
            time_mult = 60
        else:
            time_mult = 15

        points = period.findall('ns:Point', PUB_NS)
        logger.debug(f"Found {len(points)} <Point> entries")

        data = []
        for point in points:
            position = point.find('ns:position', PUB_NS)
            price = point.find('ns:price.amount', PUB_NS)

            if position is None or price is None or not position.text or not price.text:
                logger.warning("Missing <position> or <price.amount> in <Point>")
                continue

            time_delta = time_mult * (int(position.text) - 1)
            pos_time = period_start + timedelta(minutes=time_delta)

            data.append({
                'date': pos_time.strftime("%d-%m-%Y"),
                'hour': pos_time.strftime("%H"),
                'min': pos_time.strftime("%M"),
                'price': round(float(price.text)/10, 3)
            })
        logger.debug(f"{data}")
        logger.info(f"Parsed {len(data)} data points from XML")
        return data
    except Exception as e:
        logger.error(f"XML parsing error: {e}")
        return []

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

    logger.debug(f"Fetching data with parameters: {safe_params}")# log has security token #FIXME
    try:
        response = requests.get(config.BASE_URL, params=params)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch API data: {e}")
        return []

    return parse_xml(response.text)

def aggregate_day(data, date_str, start_hour=0, end_hour=24, last_price=0):
    """Aggregate quarter-hourly data into hourly means."""
    fxd_day = [{'date': date_str, 'hour': i, 'price': float('nan')} for i in range(24)]
    for hour in range(start_hour, end_hour):
        hour_prices = []
        for minute in [0, 15, 30, 45]:
            entry = next((item for item in data if int(item['hour']) == hour and int(item['min']) == minute), None)
            if entry:
                last_price = float(entry['price'])
            hour_prices.append(last_price)
        avg_price = mean(hour_prices) if hour_prices else float('nan')
        fxd_day[hour] = {'date': date_str, 'hour': hour, 'price': avg_price}
    return fxd_day

def fix_raw_elec_data(data) -> tuple[dict, dict]:
    #if the time went forward i.e., daylight saving starts
    #TODO: on the day DST starts and ends, the values are going to be wrong.
    # if daylight saving ends, then there will be two hr=3 entries and hr=1 is for the next day hr=[0] is todays 23:00 value.
    # This happens on last sunday of October

    if not data:
        return empty_day_data(), float('nan')

    today_date = data[0]['date']
    # Separate hour 0 (belongs to next day) from today's data
    today_main = [d for d in data if int(d['hour']) != 0]
    tmrw_hour0 = [d for d in data if int(d['hour']) == 0]
    # Aggregate today's data (1–23)
    fxd_data = aggregate_day(today_main, today_date, start_hour=1, end_hour=24)
    tmp_data = aggregate_day(tmrw_hour0, '')
    tmrw_price = tmp_data[0]['price']

    return fxd_data, tmrw_price

def elec_fetch_loop(stop_event, queue_out):
    today_data = []
    tmrw_data = []
    fxd_today_data = []
    fxd_tmrw_data = empty_day_data()
    tmrw_0hr_price = float('nan')
    ylihum_0hr_price = float('nan')

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
                fxd_today_data = today_data
                tmrw_0hr_price = ylihum_0hr_price
                tmrw_data = []
                fxd_tmrw_data = empty_day_data()
                ylihum_0hr_price = float('nan')
                last_fetch_date = today_str
                logger.info("Date changed — shifted tmrw_data to today_data.")

            if not today_data:
                fetched_tday = fetch_elec_data(now)
                if fetched_tday:
                    fxd_today_data, tmrw_0hr_price = fix_raw_elec_data(fetched_tday)
                    today_data = fxd_today_data
                    last_fetch_date = today_str
                    logger.debug("Fetched todays data")

            if today_data and now.hour >= 12 and not tmrw_data:
                next_day = now + timedelta(days=1)
                fetched_tmrw = fetch_elec_data(next_day)
                if fetched_tmrw:
                    fxd_tmrw_data, ylihum_0hr_price = fix_raw_elec_data(fetched_tmrw)
                    fxd_tmrw_data[0]['price'] = tmrw_0hr_price
                    tmrw_data = fxd_tmrw_data
                    logger.debug("Fetched tmrw data")

            if today_data:
                data_bundle = {
                    'today': fxd_today_data,
                    'tmrw': fxd_tmrw_data
                }
                if data_bundle != last_sent_data:
                    queue_out.put(data_bundle)
                    last_sent_data = data_bundle
                    logger.info("Sent fixed data to renderer.")

            now = datetime.now()
            next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0);
            seconds_till_next_day = (next_day - now).seconds
            # Decide sleep interval
            if today_data and tmrw_data:
                sleep_duration = config.SLEEP_DUR_DATA_AVLBL
            elif today_data:
                sleep_duration = config.SLEEP_DUR_NO_TMRW_DATA
            else:
                sleep_duration = config.SLEEP_DUR_NO_DATA
            
            if (sleep_duration > seconds_till_next_day):
                sleep_duration = seconds_till_next_day
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
