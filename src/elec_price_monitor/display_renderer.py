from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import matplotlib.font_manager as fm
from queue import Empty
import time
import zlib
from . import config
from .log import Log
# from rest_fetcher import fetch_elec_data

# no way render_iamge will work correctly if these parameters change, so no point in putting them in config
WIDTH, HEIGHT = 648, 480
BAT_BODY_WIDTH = 65
BAT_BODY_HEIGHT = 25
BAT_STUB_WIDTH = 6
BAT_STUB_HEIGHT = 10
# ROTATE_DEGREES = -90
FONT_SIZE_HEADER = 50
FONT_SIZE_NORM = 20
ROW_COUNT = 24

logger = Log.get_logger(__name__)
Log().change_log_level(__name__, Log.DEBUG)

def draw_battery(draw: ImageDraw.ImageDraw, x: int, y: int, level: int, font: ImageFont.ImageFont):
    # Configs
    radius = 3  # Rounded corner radius
    # Battery body rectangle
    body_box = [x, y, x + BAT_BODY_WIDTH, y + BAT_BODY_HEIGHT]
    # Rounded rectangle (battery body)
    draw.rounded_rectangle(body_box, radius=radius, outline=(0, 0, 0), width=3, fill=None)

    # Battery stub (terminal)
    stub_x0 = x - BAT_STUB_WIDTH
    stub_y0 = y + (BAT_BODY_HEIGHT - BAT_STUB_HEIGHT) // 2
    stub_x1 = stub_x0 + BAT_STUB_WIDTH
    stub_y1 = stub_y0 + BAT_STUB_HEIGHT
    draw.rectangle([stub_x0, stub_y0, stub_x1, stub_y1], fill=(0, 0, 0))

    # Battery level text inside body
    percent_text = f"{level}%"
    bbox = draw.textbbox((0, 0), percent_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    text_x = x + (BAT_BODY_WIDTH - text_w) // 2
    text_y = y + (BAT_BODY_HEIGHT - text_h) // 2 - 3

    if (level <= 10):
        draw.text((text_x, text_y), percent_text, font=font, fill=(255, 0, 0))
    else:
        draw.text((text_x, text_y), percent_text, font=font, fill=(0, 0, 0))
def get_font(font_name, font_size):
    font_paths = fm.findSystemFonts(fontpaths=None, fontext='ttf')
    for path in font_paths:
        filename = path.split('/')[-1].split('\\')[-1]
        if filename.lower() == (font_name.lower() + '.ttf'):
            logger.debug(f'found font {path = }, {font_size =}')
            return ImageFont.truetype(path, font_size)

    logger.error(f'Failed to find font: {font_name = }, {font_size = }')
    raise Exception("Failed to find font")
    #return font_path;
def render_image(device:dict, today_data:dict, tmrw_data:dict, now:datetime) -> Image.Image:
    image = Image.new('RGB', (WIDTH, HEIGHT), 'white')
    draw = ImageDraw.Draw(image)

    font_header = get_font('DejaVuSans-Bold', 20)#"DejaVuSans-Bold.ttf", FONT_SIZE_HEADER)
    font_row = get_font('DejaVuSansMono', 20)#"DejaVuSans.ttf", FONT_SIZE_NORM)
    font_row_bold = get_font('DejaVuSansMono-Bold', 20)#"DejaVuSans.ttf", FONT_SIZE_NORM)
    font_batt = get_font('DejaVuSans', 20)
    # except IOError:
    #     raise
    #     font_header = ImageFont.load_default()
    #     font_row = ImageFont.load_default()

        # Header
    hdr_str = f"{today_data[0]['date']}"
    # hdr_str = f'{device['date']}    Battery: {device['batt']}%'

    # print(f'{hdr_str:^{324-len(hdr_str)}}')
    # draw.text((0, 10), f'{hdr_str}', font=font_header, fill=(0, 0, 0))
    hdr_y = 10;
    bbox = draw.textbbox((0, 0), hdr_str, font=font_header)
    text_width = bbox[2] - bbox[0]
    x_pos = (WIDTH - text_width) // 2
    draw.text((x_pos, hdr_y), hdr_str, font=font_header, fill=(0, 0, 0))
    draw_battery(draw, x=WIDTH - 80, y=hdr_y, level=device['batt'], font=font_batt)

    dividr_y = hdr_y + BAT_BODY_HEIGHT + 2
    draw.line((0, dividr_y, WIDTH, dividr_y), width=2, fill=(0, 0, 0))
    # Rows start below header
    start_y = dividr_y + 2
    row_height = (HEIGHT - start_y - 5 - 2) // 24  # fit 24 rows

    for i in range(24):
        y = start_y + i * row_height

        hour = today_data[i]['hour']
        # print(f'{hour = }, {now.hour = }')
        if int(hour) == now.hour:
            font_to_use = font_row_bold
            txt_col = (255,0,0)
        else:
            font_to_use = font_row
            txt_col = (0, 0, 0)


        price_today = today_data[i]['price']
        price_tmrw = tmrw_data[i]['price']

        draw.text((10, y), f"{hour:>02}:00", font=font_to_use, fill=txt_col)
        draw.text((100, y), f"{price_today:10.01f}", font=font_to_use, fill=txt_col)
        draw.text((220, y), f"{price_tmrw:10.01f}", font=font_row, fill=(0, 0, 0))

        draw.line((5, y + 2 + row_height, 340, y + 2 + row_height), width=1, fill=(0,0,0))

    draw.line((5, start_y, 5, y+row_height+1), width=1, fill=(0, 0, 0))
    draw.line((340, start_y, 340, y+row_height+1), width=1, fill=(0, 0, 0))

    return image

def gen_pixel_buff(img:Image.Image) -> tuple[bytearray, bytearray]:
    img = img.convert("RGB")
    # pixels = img.show()
    width,height = img.size

    black_buffer = bytearray()
    red_buffer = bytearray()

    for y in range(height):
        for x in range(0, width, 8):
            black_byte = 0
            red_byte = 0

            for i in range(8):
                pixel = img.getpixel((x + i, y))

                # MSB first, so bit index = 7 - i
                bit = 1 << (7 - i)

                # Basic thresholding: exact match
                if pixel == (0, 0, 0):  # Black
                    black_byte |= bit
                elif pixel in [(255, 0, 0), (200, 0, 0)]:  # Red (tolerate dark red)
                    red_byte |= bit
                # else white or other color → 0 in both

            black_buffer.append(black_byte)
            red_buffer.append(red_byte)

    return black_buffer, red_buffer

# def rle_encode(data: bytes) -> bytes:
#     """Run-Length Encode a bytes-like object.
#     Output format: [value][count][value][count]...
#     """
#     if not data:
#         return b""
#
#     output = bytearray()
#     prev_byte = data[0]
#     count = 1
#
#     for b in data[1:]:
#         if b == prev_byte and count < 255:
#             count += 1
#         else:
#             output.append(prev_byte)
#             output.append(count)
#             prev_byte = b
#             count = 1
#
#     # Add last run
#     output.append(prev_byte)
#     output.append(count)
#
#     return bytes(output)
def renderer_loop(stop_event, elec_data_queue, status_queue, img_data_queue):
    latest_today_data = []
    latest_tmrw_data = []
    latest_device = {'batt': 0, 'date': '00-00-0000'}

    while not stop_event.is_set():
        try:
            data = elec_data_queue.get(timeout=1.0)  # BLOCKING: wait for first data
            latest_today_data = data.get("today", [])
            latest_tmrw_data = data.get("tmrw", [])
            break
        except Empty:
            continue

    if not latest_today_data:
        logger.error(f"should not have gotten empty data. Killing the thread.")
        raise RuntimeError("Invalid data: 'today' dataset is missing or empty.")

    while not stop_event.is_set():
        try:
            now = datetime.now()
            try:
                while not elec_data_queue.empty(): # empty the queue
                    data = elec_data_queue.get_nowait()
                    latest_today_data = data.get("today", [])
                    latest_tmrw_data = data.get("tmrw", []) #lets do "safe" access
                    if (not latest_today_data):
                        logger.info("No new today data from the queue, using old.")
                    elif (not latest_tmrw_data):
                        logger.info("No new tmrw data from the queue, using old.")
                    else:
                        logger.debug("Updated electricity data received.")
            except Empty:
                pass  # No new data — continue with last known values

            try:
                while not status_queue.empty(): # empty the queue if there is more than one status avlbl
                    latest_device = status_queue.get_nowait()
                    logger.debug(f"Updated device status: {latest_device}")
            except Empty:
                logger.debug("No new device info. Using last known device state.")

            try:
                img = render_image(latest_device, latest_today_data, latest_tmrw_data, now)
                red_buf, blk_buf = gen_pixel_buff(img)
                # red_encoded_buf = rle_encode(red_buf)
                # img_data_queue.put((red_buf, blk_buf))
                red_zlib_buf = zlib.compress(red_buf, 9)
                blk_zlib_buf = zlib.compress(blk_buf, 9)
                img_data_queue.put((red_zlib_buf, blk_zlib_buf))
                if (config.DEBUG and config.DUMP_IMG_BUFF):
                    logger.debug(f"Saving raw buffers")
                    with open(Log().log_dir / "red_buf_bin", 'wb') as f: f.write(red_buf)
                    with open(Log().log_dir / "blk_buf_bin", 'wb') as f: f.write(blk_buf)
                    with open(Log().log_dir / "red_buf_zbin", 'wb') as f: f.write(red_zlib_buf)
                    with open(Log().log_dir / "blk_buf_zbin", 'wb') as f: f.write(blk_zlib_buf)
                    img.save(Log().log_dir / "gen_img.png")
                # logger.error(f'{len(red_buf) =} -- {len(red_encoded_buf) =} -- {len(red_zlib_buf) =} -- {len(blk_zlib_buf) =}')
                logger.info(f"New image rendered and pushed to img_data_queue.{len(red_zlib_buf) =} -- {len(blk_zlib_buf) =}")
            except Exception as e:
                logger.error(f"Failed to render image: {e}")

            # --- 4. Sleep until next hour ---
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            # sleep_seconds = (next_hour - datetime.now().replace(second=0, microsecond=0)).total_seconds()
            sleep_seconds = (next_hour - datetime.now().replace(microsecond=0)).seconds
            logger.info(f"Sleeping for {int(sleep_seconds) =}.")
            for _ in range(sleep_seconds): # this is very bad way of exiting, i donot know any better way yet.
                time.sleep(1)
                if stop_event.is_set():
                    return
            # time.sleep(sleep_seconds)
        except Exception as e:
            logger.error(f'Exception in renderer_loop {e}')

    logger.debug(f'Called to terminate, stopping thread {__name__}')
    return