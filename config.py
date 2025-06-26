DEBUG = True
MOCK_REST_DATA = False

SLEEP_DUR_NO_DATA = 5
SLEEP_DUR_NO_TMRW_DATA = 30*60
SLEEP_DUR_DATA_AVLBL = 2*60*60

if DEBUG and MOCK_REST_DATA:
    BASE_URL = "http://localhost:5000/api"
else:
    BASE_URL = "https://web-api.tp.entsoe.eu/api"