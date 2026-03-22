from math import nan

from src.elec_price_monitor.display_renderer import render_image, gen_pixel_buff
from PIL import Image
from datetime import datetime


def test_render_image():
    now = datetime.now()
    # battery voltage has a scaling factor of 51
    device = {'batt': 4*51, 'date': '05-06-2025'}
    today_data = [{'date': '05-06-2025', 'hour': str(i), 'price': i} for i in range(24)]
    tmrw_data = [{'date': '06-06-2025', 'hour': str(i), 'price': i * 2} for i in range(24)]
    weather = {'temp_now':-10, 'feels_like':-10.12, 'temp_plus3h':1, 'temp_plus6h':-1,  't_minmax':{'min':1, 'max':10}}

    today_data[1]['price'] = nan
    today_data[2]['price'] = 20.123
    image = render_image(device, today_data, tmrw_data, now, weather)
    assert isinstance(image, Image.Image)
    assert image.size == (648, 480)

    image.save('test.png')
    #
    # device = {'batt': 100, 'date': '05-06-2025'}
    # image = render_image(device, today_data, tmrw_data)
    # image.save('test2.png')

    # device = {'batt': 10, 'date': '05-06-2025'}
    # image = render_image(device, today_data, tmrw_data, now)
    #gen_pixel_buff(image)
    #image.save('test3.png')

if __name__ == '__main__':
    test_render_image()