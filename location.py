from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # set this in Render dashboard

@app.route("/location", methods=["POST"])
def location():
    data = request.get_json()
    if not data or "wifiAccessPoints" not in data:
        return jsonify({"error": "Invalid payload"}), 400

    google_url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
    response = requests.post(google_url, json=data)
    if response.status_code == 200:
        geo = response.json()
        if "location" in geo:
            lat = geo["location"]["lat"]
            lng = geo["location"]["lng"]
            accuracy = geo.get("accuracy", 0)
            print(f"📍 Got location: {lat},{lng} (±{accuracy}m)")
            return jsonify({"lat": lat, "lng": lng, "accuracy": accuracy})
        else:
            return jsonify({"error": "No location found"}), 500
    else:
        print("❌ Google API error:", response.text)
        return jsonify({"error": "Google API error"}), response.status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
