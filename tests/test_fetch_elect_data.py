from datetime import datetime
from rest_fetcher import fetch_elec_data

def test_fetch_elect_data():
    now = datetime.now()
    data = fetch_elec_data(now)

    assert isinstance(data, dict)
