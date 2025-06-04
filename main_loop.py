import time
from rest_fetcher import fetch_sensor_data
from display_renderer import render_image, convert_to_epaper_palette, extract_masks

FETCH_INTERVAL = 60

def main_loop():
    while True:
        try:
            print("[INFO] Updating display...")
            device, status, sensors = fetch_sensor_data()
            img = render_image(device, status, sensors)
            epaper_img = convert_to_epaper_palette(img)
            bw_mask, red_mask = extract_masks(epaper_img)

            # Save output (for testing)
            epaper_img.save("./epaper_preview.png")
            bw_mask.save("./bw_layer.bmp")
            red_mask.save("./red_layer.bmp")

        except Exception as e:
            print(f"[FATAL] {e}")

        time.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    main_loop()
