from display_renderer import render_image
from PIL import Image
from datetime import datetime


def test_render_image():
    now = datetime.now()
    device = {'batt': 80, 'date': '05-06-2025'}
    today_data = [{'date': '05-06-2025', 'hour': str(i), 'price': i} for i in range(24)]
    tmrw_data = [{'date': '06-06-2025', 'hour': str(i), 'price': i * 2} for i in range(24)]

    image = render_image(device, today_data, tmrw_data, now)
    assert isinstance(image, Image.Image)
    assert image.size == (648, 480)

    # image.save('test.png')
    #
    # device = {'batt': 100, 'date': '05-06-2025'}
    # image = render_image(device, today_data, tmrw_data)
    # image.save('test2.png')

    device = {'batt': 10, 'date': '05-06-2025'}
    image = render_image(device, today_data, tmrw_data, now)
    image.save('test3.png')