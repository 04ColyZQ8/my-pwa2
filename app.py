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
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "supersecretkey")  # optionally move to env
BLYNK_TOKEN = os.getenv("BLYNK_TOKEN", "YOUR_BLYNK_TOKEN")
USERNAME = os.getenv("USERNAME", "Jamie")
PASSWORD = os.getenv("PASSWORD", "trax123")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # must be set in Render or env

# -----------------------
# Helpers
# -----------------------
def blynk_update(pin, value):
    """Send a command to Blynk cloud"""
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&pin={pin}&value={value}"
    try:
        res = requests.get(url, timeout=2)
        if res.status_code != 200:
            print(f"Blynk update failed: {res.status_code}")
        return res
    except Exception as e:
        print("Blynk update exception:", e)
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
# Auth
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
PIN_MAP = {
    "unlock": "V0",
    "lock": "V4",
    "sound": "V1",
    "stopSound": "V2",
    "flash": "V3",
    "stopFlash": "V4",
    "remoteStart": "V5",
}

@app.route('/api/<action>', methods=['POST'])
@token_required
def control_action(action):
    pin = PIN_MAP.get(action)
    if not pin:
        return jsonify({"error": "Unknown action"}), 400
    value = 1 if "stop" not in action else 0
    res = blynk_update(pin, value)
    return jsonify({"status": "sent", "response": res.text if res else "no response"})

@app.route('/api/status', methods=['GET'])
@token_required
def status():
    pins = ["V0","V1","V2","V3","V4","V5"]
    status = {}
    for pin in pins:
        try:
            res = requests.get(f"https://blynk.cloud/external/api/get?token={BLYNK_TOKEN}&pin={pin}", timeout=2)
            status[pin] = int(res.text) if res and res.status_code == 200 else 0
        except:
            status[pin] = 0
    return jsonify(status)

@app.route('/api/warmup', methods=['GET'])
@token_required
def warmup():
    for pin in ["V0","V1","V2","V3","V4","V5"]:
        blynk_update(pin, 0)
    return jsonify({"status": "warmed up"})

# -----------------------
# Geolocation
# -----------------------
@app.route('/api/geoscan', methods=['POST'])
@token_required
def geoscan():
    try:
        data = request.get_json(force=True)
        if not data or "wifiAccessPoints" not in data:
            return jsonify({"error": "invalid data"}), 400

        g_res = requests.post(
            f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}",
            json=data, timeout=4
        )
        geo = g_res.json()

        if "location" in geo:
            lat = geo["location"]["lat"]
            lng = geo["location"]["lng"]
            blynk_update("V8", f"{lat:.6f},{lng:.6f}")

        return jsonify(geo), g_res.status_code
    except Exception as e:
        print("Error in /api/geoscan:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/staticmap', methods=['GET'])
@token_required
def static_map():
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    if not lat or not lng:
        return jsonify({"error": "missing coordinates"}), 400
    url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lng}&zoom=15&size=400x300&markers=color:red%7C{lat},{lng}&key={GOOGLE_API_KEY}"
    return jsonify({"url": url})

# -----------------------
# Run Server
# -----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
