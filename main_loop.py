import time
from datetime import datetime
from rest_fetcher import fetch_sensor_data
from display_renderer import render_image, convert_to_epaper_palette, extract_masks

FETCH_INTERVAL = 60

def main_loop():
    now = datetime.now()
    print(f"Current time: {now}")

    fetch_sensor_data(now)

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
    while True:
        try:
            main_loop()
        except Exception as e:
            print(f"[Exception raised in main_loop] {e}")
            break
