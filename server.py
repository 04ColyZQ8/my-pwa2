from flask import Flask, request, jsonify, send_from_directory
import requests
import os

app = Flask(__name__, static_folder='.', static_url_path='')

# -------------------------
# Blynk Configuration
# -------------------------
BLYNK_TOKEN = "LcIEIHmUOMbwC8xi-3Au3CQM7lNajKR9"  # Your token here ✅

def blynk_update(pin, value):
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&pin={pin}&value={value}"
    return requests.get(url)

# -------------------------
# Google Geolocation
# -------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Set this in Render dashboard

def location():
    data = request.get_json()
    if not data or "wifiAccessPoints" not in data:
        return jsonify({"error": "Invalid payload"}), 400

    google_url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
    response = requests.post(google_url, json=data)
    if response.status_code == 200:
        geo = response.json()
        loc = geo.get("location", {})
        lat = loc.get("lat", 0)
        lng = loc.get("lng", 0)
        accuracy = geo.get("accuracy", 0)
        print(f"📍 Got location: {lat},{lng} (±{accuracy}m)")
        return jsonify({"lat": lat, "lng": lng, "accuracy": accuracy})
    else:
        print("❌ Google API error:", response.text)
        return jsonify({"error": "Google API error"}), response.status_code

# -------------------------
# Routes
# -------------------------
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

# -------------------------
# ESP32-friendly location endpoint
# -------------------------
# No authentication needed for ESP32
@app.route("/api/location", methods=["POST"])
def api_location():
    return location()

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
