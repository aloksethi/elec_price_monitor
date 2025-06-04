from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/api/sensors/a")
def sensors():
    return jsonify({
        "device": "EPD-01",
        "status": "OK",
        "sensors": [{"name": f"Sensor {i+1}", "status": "OK" if i % 2 == 0 else "FAIL"} for i in range(24)]
    })

if __name__ == "__main__":
    app.run(debug=True)
