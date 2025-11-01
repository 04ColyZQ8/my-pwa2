from flask import Flask, request, jsonify, send_from_directory
import requests

app = Flask(__name__, static_folder='.', static_url_path='')

BLYNK_TOKEN = "LcIEIHmUOMbwC8xi-3Au3CQM7lNajKR9"  # Your token here ✅

def blynk_update(pin, value):
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&pin={pin}&value={value}"
    return requests.get(url)

@app.route("/")
def root():
    return send_from_directory('.', 'carlockPWA.html')

@app.route("/api/unlock", methods=["POST"])
def unlock():
    res = blynk_update("V0", 1)
    return jsonify({"status": "sent", "response": res.text})

@app.route("/api/lock", methods=["POST"])
def lock():
    res = blynk_update("V4", 1)
    return jsonify({"status": "sent", "response": res.text})

@app.route("/api/status", methods=["GET"])
def status():
    url = f"https://blynk.cloud/external/api/get?token={BLYNK_TOKEN}&pin=V0"
    res = requests.get(url)
    return jsonify(res.json())
@app.route("/api/location", methods=["POST"])
def api_location():
    return location()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
