from src.elec_price_monitor.weather_fetcher import fetch_weather
def test_weather():
    weather = fetch_weather()
    print(weather)

if __name__ == '__main__':
    test_weather()