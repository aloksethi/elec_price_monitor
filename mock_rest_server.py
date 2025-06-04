from flask import Flask, Response
import random
import os

DATA_LOCATION = "test_data"
app = Flask(__name__)

XML_FILES =[
    os.path.join(DATA_LOCATION, "response_one_day_data.xml"),
    os.path.join(DATA_LOCATION, "response_when_no_data.xml"),
]

@app.route("/api", methods=['GET'])
def get_elec_data():
    #randomly pick one of the xml file and send it
    xml_file = random.choice(XML_FILES)
    xml_file = XML_FILES[0]

    with open(xml_file, "r", encoding="utf-8") as f:
        xml_data = f.read()

    return Response(xml_data, mimetype='application/xml')

if __name__ == "__main__":
    app.run(debug=True)
