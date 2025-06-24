from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import matplotlib.font_manager as fm

from local_comm import get_device_status
from rest_fetcher import fetch_elec_data

#
WIDTH, HEIGHT = 648, 480
BAT_BODY_WIDTH = 65
BAT_BODY_HEIGHT = 25
BAT_STUB_WIDTH = 6
BAT_STUB_HEIGHT = 10

ROTATE_DEGREES = -90
FONT_SIZE_HEADER = 50
FONT_SIZE_NORM = 20
ROW_COUNT = 24

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
            print(f'found font {path = }, {font_size =}')
            return ImageFont.truetype(path, font_size)

    print(f'Failed to find font: {font_name = }, {font_size = }')
    raise Exception("Failed to find font")
    #return font_path;
def render_image(device:dict, today_data:dict, tmrw_data:dict, now:datetime):
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
    pixels = img.show()

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

# def extract_masks(epaper_img):
#     bw_mask = epaper_img.convert('1')
#     red_mask = Image.new('1', epaper_img.size, color=1)
#     epixels = epaper_img.load()
#     rpixels = red_mask.load()
#
#     for y in range(epaper_img.height):
#         for x in range(epaper_img.width):
#             if epixels[x, y] == (255, 0, 0):
#                 rpixels[x, y] = 0
#
#     return bw_mask, red_mask

# if (__name__ == "__main__"):
#
#     device = get_device_status()
#     today_data = fetch_elec_data(datetime.now())
#
#     img = render_image(device, today_data, today_data)
#
#     img.save("output_test.png")