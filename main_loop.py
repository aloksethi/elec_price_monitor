import time
from datetime import datetime, timedelta
from rest_fetcher import fetch_elec_data
from display_renderer import render_image, convert_to_epaper_palette, extract_masks
from local_comm import get_device_status
from log import Log

FETCH_INTERVAL = 60


def main_loop():
    now = datetime.now()
    logger.debug(f"Current time: {now}")
    logger.debug(f"Current time: {now+1}")

#make sure the loop runs whenever the hour changes
    today_data = fetch_elec_data(now)
    tmrw_data = fetch_elec_data(now + timedelta(days=1))
    device = get_device_status()

    img = render_image(device, today_data, tmrw_data, now)

    raise Exception("testing")
"""
    print("[INFO] Updating display...")
    device, status, sensors = fetch_sensor_data()
    img = render_image(device, status, sensors)
    epaper_img = convert_to_epaper_palette(img)
    bw_mask, red_mask = extract_masks(epaper_img)

    # Save output (for testing)
    epaper_img.save("./epaper_preview.png")
    bw_mask.save("./bw_layer.bmp")
    red_mask.save("./red_layer.bmp")


time.sleep(FETCH_INTERVAL)
"""

if __name__ == "__main__":
    logger = Log.get_logger("main")
    Log().change_log_level("main", Log.DEBUG)
    while True:
        try:
            main_loop()
        except Exception as e:
            logger.error(f"[Exception raised in main_loop] {e}")
            break
