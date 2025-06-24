from flask import Flask, Response
import random
import os

DATA_LOCATION = "test_data"
app = Flask(__name__)

XML_FILES =[
    os.path.join(DATA_LOCATION, "Energy_Prices_202506230000-202506230100.xml"),
    os.path.join(DATA_LOCATION, "response_when_no_data.xml"),
    os.path.join(DATA_LOCATION, "response_one_day_data.xml"),
]
serv_idx = 0
@app.route("/api", methods=['GET'])

def get_elec_data():
    global serv_idx
    #randomly pick one of the xml file and send it
    xml_file = random.choice(XML_FILES)
    xml_file = XML_FILES[serv_idx]
    serv_idx = (serv_idx + 1)%2#len(XML_FILES)

    with open(xml_file, "r", encoding="utf-8") as f:
        xml_data = f.read()

    return Response(xml_data, mimetype='application/xml')

if __name__ == "__main__":
    app.run(debug=True)
