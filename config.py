DEBUG = True
MOCK_REST_DATA = False

SLEEP_DUR_NO_DATA:int = 5
SLEEP_DUR_NO_TMRW_DATA:int = 30*60
SLEEP_DUR_DATA_AVLBL:int = 2*60*60

if DEBUG and MOCK_REST_DATA:
    BASE_URL = "http://localhost:5000/api"
else:
    BASE_URL = "https://web-api.tp.entsoe.eu/api"

PY_PORT = 6666 #udp port for the server running at python
UC_PORT = 6667 #udp port for the server running at uC