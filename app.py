from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, jwt, datetime
from functools import wraps
import os

app = Flask(__name__)
CORS(app)

# -----------------------
# Config
# -----------------------
app.config['SECRET_KEY'] = 'supersecretkey'  # keep this safe, maybe move to env var later
BLYNK_TOKEN = "LcIEIHmUOMbwC8xi-3Au3CQM7lNajKR9"

USERNAME = "Jamie"
PASSWORD = "trax123"

# Load Google Maps API key from environment
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


# -----------------------
# Helpers
# -----------------------
def blynk_update(pin, value):
    """Send a command to Blynk cloud"""
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&pin={pin}&value={value}"
    try:
        res = requests.get(url, timeout=2)
        return res
    except:
        return None

# -----------------------
# JWT Auth
# -----------------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token missing'}), 401
        try:
            token = token.replace("Bearer ", "")
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except Exception as e:
            print("JWT decode error:", e)
            return jsonify({'message': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

# -----------------------
# Auth Endpoint
# -----------------------
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data and data.get('username') == USERNAME and data.get('password') == PASSWORD:
        token = jwt.encode(
            {'user': USERNAME, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)},
            app.config['SECRET_KEY'], algorithm="HS256"
        )
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid credentials'}), 401

# -----------------------
# Control Endpoints
# -----------------------
@app.route('/api/unlock', methods=['POST'])
@token_required
def unlock():
    res = blynk_update("V0", 1)
    return jsonify({"status": "sent", "response": res.text if res else "dummy response"})

@app.route('/api/lock', methods=['POST'])
@token_required
def lock():
    res = blynk_update("V4", 1)
    return jsonify({"status": "sent", "response": res.text if res else "dummy response"})

@app.route('/api/sound', methods=['POST'])
@token_required
def sound_alarm():
    res = blynk_update("V1", 1)
    return jsonify({"status": "sent", "response": res.text if res else "dummy response"})

@app.route('/api/stopSound', methods=['POST'])
@token_required
def stop_alarm():
    res = blynk_update("V2", 1)
    return jsonify({"status": "sent", "response": res.text if res else "dummy response"})

@app.route('/api/flash', methods=['POST'])
@token_required
def flash_lights():
    res = blynk_update("V3", 1)
    return jsonify({"status": "sent", "response": res.text if res else "dummy response"})

@app.route('/api/stopFlash', methods=['POST'])
@token_required
def stop_flash_lights():
    res = blynk_update("V4", 0)
    return jsonify({"status": "sent", "response": res.text if res else "dummy response"})

@app.route('/api/remoteStart', methods=['POST'])
@token_required
def remote_start():
    res = blynk_update("V5", 1)
    return jsonify({"status": "sent", "response": res.text if res else "dummy response"})

@app.route('/api/status', methods=['GET'])
@token_required
def status():
    url = f"https://blynk.cloud/external/api/get?token={BLYNK_TOKEN}&pin=V0"
    try:
        res = requests.get(url, timeout=2)
        return jsonify(res.json())
    except:
        return jsonify({"V0": 0, "V4": 0, "V1": 0, "V2": 0, "V3": 0, "V5": 0})

# -----------------------
# Warmup Endpoint
# -----------------------
@app.route('/api/warmup', methods=['GET'])
@token_required
def warmup():
    pins = ["V0", "V1", "V2", "V3", "V4", "V5"]
    for pin in pins:
        blynk_update(pin, 0)
    return jsonify({"status": "warmed up"})

# -----------------------
# Google Map Proxy (key stays hidden)
# -----------------------
@app.route('/api/staticmap', methods=['GET'])
@token_required
def static_map():
    """
    Securely generate a Google Static Map image without exposing the API key.
    The frontend calls this endpoint, passing lat/lng as query params.
    """
    lat = request.args.get("lat")
    lng = request.args.get("lng")

    if not lat or not lng:
        return jsonify({"error": "missing coordinates"}), 400

    google_url = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={lat},{lng}&zoom=15&size=400x300&markers=color:red%7C{lat},{lng}&key={GOOGLE_API_KEY}"
    )

    return jsonify({"url": google_url})

# -----------------------
# Google Geolocation Scan
# -----------------------
@app.route('/api/geoscan', methods=['POST'])
@token_required
def geoscan():
    """
    Receives Wi-Fi scan JSON from ESP32, forwards to Google Geolocation API,
    and updates Blynk V8 with coordinates.
    """
    try:
        data = request.get_json(force=True)
        if not data or "wifiAccessPoints" not in data:
            return jsonify({"error": "invalid data"}), 400

        google_url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
        g_res = requests.post(google_url, json=data, timeout=4)
        geo = g_res.json()

        # update Blynk map widget (V8)
        if "location" in geo:
            lat = geo["location"]["lat"]
            lng = geo["location"]["lng"]
            coord = f"{lat:.6f},{lng:.6f}"
            blynk_update("V8", coord)

        return jsonify(geo), g_res.status_code
    except Exception as e:
        print("Error in /api/geoscan:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# Run Server
# -----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
