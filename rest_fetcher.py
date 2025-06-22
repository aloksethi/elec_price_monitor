import requests
import os
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
from log import Log

API_URL = "http://localhost:5000/api"

logger = Log.get_logger(__name__)
Log().change_log_level(__name__, Log.DEBUG)


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
                'price': float(price.text)
            })
        logger.debug(f"{data}")
        logger.info(f"Parsed {len(data)} data points from XML")
        return data
    except ET.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while parsing XML: {e}")
        raise

def fetch_elec_data(dt:datetime) ->dict:

    api_token = os.environ.get("API_TOKEN")
    if  not api_token:
        logger.error("Missing API_TOKEN environment variable")
        raise ValueError("Missing API_TOKEN environment variable")
    try:
        response = requests.get(API_URL, timeout=5)
        response.raise_for_status()
        data = response.text
        data = parse_xml(response.text)
        #print(data)
        #status = data.get("status", "UNKNOWN")
        #device = data.get("device", "UNDEFINED")
        #sensors = [(s.get("name", ""), s.get("status", "")) for s in data.get("sensors", [])]

    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch API data: {e}")

    return data
