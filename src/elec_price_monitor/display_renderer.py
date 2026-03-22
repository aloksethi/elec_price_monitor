import PIL.ImageDraw
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend (works headless and on Windows/Linux)
import matplotlib.font_manager as fm
from queue import Empty
import time
import zlib
import math
from elec_price_monitor import config
from elec_price_monitor.log import Log
# from rest_fetcher import fetch_elec_data

# no way render_iamge will work correctly if these parameters change, so no point in putting them in config
WIDTH, HEIGHT = 648, 480
# BAT_BODY_WIDTH = 65
# BAT_BODY_HEIGHT = 20
# BAT_STUB_WIDTH = 6
# BAT_STUB_HEIGHT = 10
# ROTATE_DEGREES = -90
FONT_SIZE_BIG = 50
FONT_SIZE_NORM = 20
FONT_SIZE_SMALL = 16
ROW_COUNT = 24

LEFT_PAD  = 0
TIME_W    = 70
PRICE_W   = 150
SIDEBAR_W = WIDTH - TIME_W - 2*PRICE_W
DASH_ON     = 2
DASH_OFF    = 8

logger = Log.get_logger(__name__)
Log().change_log_level(__name__, Log.DEBUG)

def battery_level_to_pctg(reported_v):
    SCALING_FACTOR = 255/5 #UINT8_MAX/5
    actual_voltage = reported_v/float(SCALING_FACTOR)
    logger.info(f"{reported_v=}, {actual_voltage=}.")

    if actual_voltage > 3.9:        # 1.3 * 3
        level = 100
    elif actual_voltage > 3.825:   # 1.275 *3
        level = 80
    elif actual_voltage > 3.75:   # 1.25 *3
        level = 60
    elif actual_voltage > 3.6:   # 1.2 *3
        level = 40
    elif actual_voltage > 3.36:   # 1.25 *3    
        level = 10
    else:
        level = 0
    
    return level
def draw_battery(draw: ImageDraw.ImageDraw, x: int, y: int, level: int, font: ImageFont.ImageFont):
    # Configs
    radius = 3  # Rounded corner radius
    # Battery body rectangle
    body_box = [x, y, x + BAT_BODY_WIDTH, y + BAT_BODY_HEIGHT]
    # Rounded rectangle (battery body)
    draw.rounded_rectangle(body_box, radius=radius, outline=(255, 255, 255), width=3, fill=None)

    # Battery stub (terminal)
    stub_x0 = x - BAT_STUB_WIDTH
    stub_y0 = y + (BAT_BODY_HEIGHT - BAT_STUB_HEIGHT) // 2
    stub_x1 = stub_x0 + BAT_STUB_WIDTH
    stub_y1 = stub_y0 + BAT_STUB_HEIGHT
    draw.rectangle([stub_x0, stub_y0, stub_x1, stub_y1], fill=(255, 255, 255))

    # Battery level text inside body
    percent_text = f"{battery_level_to_pctg(level)}"
    bbox = draw.textbbox((0, 0), percent_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    text_x = x + (BAT_BODY_WIDTH - text_w) // 2
    text_y = y + (BAT_BODY_HEIGHT - text_h) // 2 - 3

    if (level <= 10):
        draw.text((text_x, text_y), percent_text, font=font, fill=(255, 0, 0))
    else:
        draw.text((text_x, text_y), percent_text, font=font, fill=(255, 255, 255))
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

def is_num(x):
    try:
        return (x is not None) and (not isinstance(x, bool)) and (not math.isnan(float(x)))
    except Exception:
        return False



def render_image(device:dict, today_data:dict, tmrw_data:dict, now:datetime, weather) -> Image.Image:

    """
    Render a 648x480 (default) e-paper image with:
      - 24 rows: Time | Today Avg | Tomorrow Avg
      - Row separators on every row (dotted)
      - Today column shows ▲/▼ vs today's daily avg
      - Only the current hour's Today cell highlighted in red
      - Right-side weather panel (Now + feels-like, +3h, +6h, precip 3h/6h, tomorrow min/max)

    Parameters
    ----------
    device : dict
        {
          'width': 648,
          'height': 480,
          'bg': (0,0,0),
          'fg': (255,255,255),
          'red': (255,0,0),
          'font_path_bold': '/path/to/your/bold.ttf',  # optional
          'font_size': 20,        # ~20 px, bold, for rows
          'font_size_small': 16,  # for headers and weather panel
          'left_pad': 6,          # left padding of table
          'sidebar_w': 150,       # weather panel width
          'col_time_w': 86,       # compressed time column width
          'col_today_w': 150,     # compressed today col width
          # tomorrow width is computed to fill remaining space
        }

    today_data : list[24] of dict
        {
          'date': '05-06-2025',
          'hour': str(i),
          'price': i
        }

    tmrw_data : list[24] of dict
        {
          'date': '05-06-2025',
          'hour': str(i),
          'price': i
        }

    now : datetime
        Current local time; used for date string and current-hour highlight.

    weather : dict-like
        May contain any subset; absent keys are simply omitted from the panel:
        {
          'temp_now': int|float,
          'feels_like': int|float,       # shown in parentheses
          'temp_plus3h': int|float,
          'temp_plus6h': int|float,
          'precip3h': {'rain': int, 'snow': int},
          'precip6h': {'rain': int, 'snow': int},
          't_minmax': {'min': int, 'max': int},  # tomorrow
        }

    Returns
    -------
    PIL.Image.Image
    """

    white_col = (255, 255, 255)
    red_col = (255, 0, 0)
    time_x  = LEFT_PAD
    today_x = time_x + TIME_W
    tmrw_x  = today_x + PRICE_W
    sidebar_x = tmrw_x + PRICE_W + 0

    image = Image.new('RGB', (WIDTH, HEIGHT), 'black')
    draw = ImageDraw.Draw(image)

    font_header = get_font('DejaVuSans-Bold', FONT_SIZE_NORM)
    font_row_bold = get_font('DejaVuSans-Bold', FONT_SIZE_SMALL)
    font_row = get_font('DejaVuSans', FONT_SIZE_SMALL)

    def draw_center_text(_x, _y, _width, _txt, _font, _color):
        bbox = draw.textbbox((0, 0), _txt, font=_font)
        text_width = bbox[2] - bbox[0]
        x_pos = _x + (_width - text_width) // 2
        draw.text((x_pos, _y), _txt, font=_font, fill=_color)

    def draw_price(_x, _y, _price, _avg, _font, _color):
        t1 = "—" if not is_num(_price) else f"{float(_price):>05.1f}"
        mark = "▲" if _price > _avg else ("▼" if _price < _avg else "")
        tmp = f"{mark + " " + t1}"
        draw_center_text(_x, _y, PRICE_W, tmp, _font, txt_col)

    def avg_val(_data):
        tmp = [v['price']
                       for v in _data
                       if v['price'] is not None and not math.isnan(float(v['price']))
                       ]
        return round(sum(tmp) / len(tmp),1) if tmp else None

    # Top row
    date_str = f"{today_data[0]['date']}"
    draw_center_text(0, 0, WIDTH, date_str, font_header, white_col)
    nxt_y = FONT_SIZE_NORM

    draw.line([(0, nxt_y + 1), (WIDTH, nxt_y + 1)], width=1)
    nxt_y = nxt_y + 1

    # header row
    header_y = nxt_y
    draw_center_text(time_x, header_y, TIME_W, "Time", font_row_bold, white_col)
    draw_center_text(today_x, header_y, PRICE_W, "Today Avg", font_row_bold, white_col)
    draw_center_text(tmrw_x, header_y, PRICE_W, "Tomorrow Avg", font_row_bold, white_col)
    nxt_y = nxt_y + FONT_SIZE_SMALL

    # row separator lines
    data_top = nxt_y
    available_h = HEIGHT - data_top - 2
    row_h = max(available_h // 24, FONT_SIZE_SMALL)  # guarantees 24 rows within the space
    bottom = data_top + row_h * 24
    # Dashed row separators (every row)
    for i in range(25):
        y = data_top + i * row_h
        x = 0
        while x < WIDTH:
            if (x >= TIME_W + PRICE_W + PRICE_W) and (i):
                break
            draw.line([(x, y), (min(x + DASH_ON, WIDTH), y)], fill=white_col, width=1)
            x += DASH_ON + DASH_OFF

    # Vertical guides TODO COME BACK HERE n check this 6
    draw.line([(today_x, header_y), (today_x, bottom)], fill=white_col, width=1)
    draw.line([(tmrw_x, header_y), (tmrw_x, bottom)], fill=white_col, width=1)
    draw.line([(sidebar_x, header_y), (sidebar_x, bottom)], fill=white_col, width=1)


    today_avg = avg_val(today_data)
    tmrw_avg = avg_val(tmrw_data)

    # Row renderer
    for i in range(24):
         y = nxt_y + i * row_h + (row_h - FONT_SIZE_SMALL) // 2

         hour = today_data[i]['hour']
         price_today = today_data[i]['price']
         price_tmrw = tmrw_data[i]['price']

         if int(hour) == now.hour:
             font_to_use = font_row_bold
             txt_col = red_col
         else:
             font_to_use = font_row_bold
             txt_col = white_col

         draw_center_text(time_x, y, TIME_W, f"{hour:>02}:00", font_to_use, txt_col)
         draw_price(today_x, y, price_today, today_avg, font_to_use, font_to_use)
         draw_price(tmrw_x, y, price_tmrw, tmrw_avg, font_to_use, font_to_use)

    # ---------- Weather sidebar ----------
    draw_center_text(sidebar_x, header_y, SIDEBAR_W, "Weather", font_row_bold, white_col)
    nxt_y = data_top + 2

    def draw_weather_line(_txt: str):
        nonlocal nxt_y
        draw_center_text(sidebar_x, nxt_y, SIDEBAR_W, _txt, font_row_bold, white_col)
        nxt_y += (FONT_SIZE_SMALL + 2)

    # Weather can be dict-like; use getattr/get to be forgiving
    def get_nested(m, *keys):
        cur = m
        for k in keys:
            try:
                cur = cur.get(k) if isinstance(cur, dict) else getattr(cur, k, None)
            except Exception:
                return None
        return cur

    temp_now = get_nested(weather, 'temp_now')
    feels_like = get_nested(weather, 'feels_like')
    t_plus3 = get_nested(weather, 'temp_plus3h')
    t_plus6 = get_nested(weather, 'temp_plus6h')
    precip3 = get_nested(weather, 'precip3h')
    precip6 = get_nested(weather, 'precip6h')
    tmm = get_nested(weather, 't_minmax')

    # Current temp (+ feels like)
    if temp_now is not None:
        if feels_like is not None:
            draw_weather_line(f"Now: {temp_now}° ({feels_like}°)")
        else:
            draw_weather_line(f"Now: {temp_now}°")

    # +3h and +6h temperatures
    if t_plus3 is not None:
        draw_weather_line(f"+3h: {t_plus3}°")
    if t_plus6 is not None:
        draw_weather_line(f"+6h: {t_plus6}°")

    # Precipitation helper: render compact Rxx% Syy%
    def fmt_precip(p):
        if not isinstance(p, dict):
            return None
        parts = []
        r = p.get('rain', None)
        s = p.get('snow', None)
        if r is not None:
            parts.append(f"R{int(r)}%")
        if s is not None:
            parts.append(f"S{int(s)}%")
        return " ".join(parts) if parts else None

    p3s = fmt_precip(precip3)
    p6s = fmt_precip(precip6)
    if p3s:
        draw_weather_line(f"Precip 3h: {p3s}")
    if p6s:
        draw_weather_line(f"Precip 6h: {p6s}")

    # Tomorrow min/max
    if isinstance(tmm, dict) and (tmm.get('min') is not None) and (tmm.get('max') is not None):
        draw_weather_line(f"Tomorrow: {int(tmm['min'])}°/{int(tmm['max'])}°")

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
def renderer_loop(stop_event, elec_data_queue, status_queue, img_data_queue, weather_data_queue=None):
    latest_today_data = []
    latest_tmrw_data = []
    latest_device = {'batt': 0, 'date': '00-00-0000'}
    latest_weather = {}

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
            logger.debug(f"starting renderer after sleep.")
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

            if weather_data_queue is not None:
                try:
                    while not weather_data_queue.empty():
                        latest_weather = weather_data_queue.get_nowait()
                        logger.debug("Updated weather data.")
                except Empty:
                    pass

            try:
                img = render_image(latest_device, latest_today_data, latest_tmrw_data, now, latest_weather)
                red_buf, blk_buf = gen_pixel_buff(img)
                # red_encoded_buf = rle_encode(red_buf)
                # img_data_queue.put((red_buf, blk_buf))
                red_zlib_buf = zlib.compress(red_buf, 9)
                blk_zlib_buf = zlib.compress(blk_buf, 9)
                img_data_queue.put((red_zlib_buf, blk_zlib_buf))
                if (config.DUMP_IMG_BUFF):
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
