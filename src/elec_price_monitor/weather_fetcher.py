"""
Fetch weather from FMI opendata.fmi.fi (WFS).
Observations: current hourly temperature.
Forecast: temperature at +3h and +6h (ECMWF).
All request times in UTC.
"""
import logging

from elec_price_monitor.log import Log
from elec_price_monitor import config
import requests
import xml.etree.ElementTree as ET
import time
from datetime import datetime, timedelta, timezone

logger = Log.get_logger(__name__)
Log().change_log_level(__name__, Log.WARNING)

FMI_WFS_BASE = "https://opendata.fmi.fi/wfs"


def _parse_parameter_value(elem) -> float | None:
    """Get numeric ParameterValue from BsWfsElement; return None for NaN or missing."""
    pv = elem.find(".//{http://xml.fmi.fi/schema/wfs/2.0}ParameterValue")
    if pv is None or pv.text is None:
        return None
    raw = pv.text.strip()
    if raw.upper() == "NAN" or raw == "":
        return None
    try:
        return round(float(raw), 1)
    except ValueError:
        return None
def _fetch_data(params):
    r = None
    for attempt in range(3):
        try:
            r = requests.get(FMI_WFS_BASE, params=params, timeout=15)
            r.raise_for_status()
            logger.debug(r.request.url)
            break
        except Exception as e:
            if attempt == 2:
                logger.error(f"FMI forecast request failed after 3 attempts: {e}")
                return None
            logger.warning(f"FMI forecast request failed (attempt {attempt + 1}/3): {e}")
            time.sleep(1)
    try:
        root = ET.fromstring(r.text)
        member = root.find(".//{http://www.opengis.net/wfs/2.0}member")
        if member is None:
            return None
        return _parse_parameter_value(member)
    except ET.ParseError as e:
        logger.error(f"FMI forecast XML parse error: {e}")
        return None

def fetch_observations(fmisid: int) -> float | None:
    """
    Fetch current hourly temperature (TA_PT1H_AVG) for the current UTC hour.
    Returns temperature in °C or None.
    """
    now_utc = datetime.now(timezone.utc)
    starttime = now_utc.strftime("%Y-%m-%dT%H:00:00Z")
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "getFeature",
        "storedquery_id": "fmi::observations::weather::hourly::simple",
        "fmisid": fmisid,
        "starttime": starttime,
        "parameters": "TA_PT1H_AVG",
    }
    val = _fetch_data(params)
    return val
def fetch_forecast(fmisid: int, utc_time: datetime) -> float | None:
    """
    Fetch forecast temperature for one UTC time (starttime = endtime).
    Returns temperature in °C or None.
    """
    t_str = utc_time.strftime("%Y-%m-%dT%H:00:00Z")
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "getFeature",
        "storedquery_id": "ecmwf::forecast::surface::point::simple",
        "fmisid": fmisid,
        "starttime": t_str,
        "endtime": t_str,
        "parameters": "temperature",
    }
    val = _fetch_data(params)
    return val
def fetch_weather() -> dict:
    """
    Build display weather dict: temp_now, temp_plus3h, temp_plus6h.
    Uses config.FMI_FMISID. All times UTC.
    """
    # fmisid = getattr(config, "FMI_FMISID", 108040)
    fmisid = config.FMI_FMISID

    now_utc = datetime.now(timezone.utc)
    temp_now = fetch_observations(fmisid)
    t_plus3 = fetch_forecast(fmisid, now_utc + timedelta(hours=3))
    t_plus6 = fetch_forecast(fmisid, now_utc + timedelta(hours=6))
    out = {}
    if temp_now is not None:
        out["temp_now"] = int(temp_now) if temp_now == int(temp_now) else temp_now
    if t_plus3 is not None:
        out["temp_plus3h"] = int(t_plus3) if t_plus3 == int(t_plus3) else t_plus3
    if t_plus6 is not None:
        out["temp_plus6h"] = int(t_plus6) if t_plus6 == int(t_plus6) else t_plus6
    return out


def weather_fetch_loop(stop_event, queue_out):
    """Loop: fetch weather, put dict in queue, sleep WEATHER_FETCH_INTERVAL."""
    interval = getattr(config, "WEATHER_FETCH_INTERVAL", 30 * 60)
    while not stop_event.is_set():
        try:
            data = fetch_weather()
            if data:
                queue_out.put(data)
                logger.info(f"Weather data sent to renderer: {data}")
        except Exception as e:
            logger.error(f"weather_fetch_loop: {e}")
        for _ in range(interval):
            if stop_event.is_set():
                return
            time.sleep(1)
