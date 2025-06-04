from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 600, 800
ROTATE_DEGREES = -90
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_SIZE = 20
ROW_COUNT = 24

def render_image(device, status, table_data):
    image = Image.new('RGB', (WIDTH, HEIGHT), 'white')
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except:
        font = ImageFont.load_default()

    draw.text((WIDTH // 2, 10), "Sensor Overview", font=font, fill='black', anchor='ma')

    row_height = (HEIGHT - 100) // ROW_COUNT
    start_y = 40
    for i, (label, state) in enumerate(table_data):
        y = start_y + i * row_height
        draw.text((20, y), label, font=font, fill='black')
        draw.text((WIDTH - 20, y), state, font=font, fill='black', anchor='ra')
        draw.line([(10, y + row_height - 2), (WIDTH - 10, y + row_height - 2)], fill=(200, 200, 200))

    footer_text = f"Device: {device} | Status: {status}"
    draw.text((WIDTH // 2, HEIGHT - 30), footer_text, font=font, fill='red', anchor='ma')

    return image.rotate(ROTATE_DEGREES, expand=True)


def convert_to_epaper_palette(img):
    img = img.convert("RGB")
    pixels = img.load()

    for y in range(img.height):
        for x in range(img.width):
            r, g, b = pixels[x, y]
            if r > 200 and g > 200 and b > 200:
                pixels[x, y] = (255, 255, 255)
            elif r > 180 and g < 100 and b < 100:
                pixels[x, y] = (255, 0, 0)
            else:
                pixels[x, y] = (0, 0, 0)
    return img


def extract_masks(epaper_img):
    bw_mask = epaper_img.convert('1')
    red_mask = Image.new('1', epaper_img.size, color=1)
    epixels = epaper_img.load()
    rpixels = red_mask.load()

    for y in range(epaper_img.height):
        for x in range(epaper_img.width):
            if epixels[x, y] == (255, 0, 0):
                rpixels[x, y] = 0

    return bw_mask, red_mask
