from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests, jwt, datetime, os, json, time
from functools import wraps

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# -----------------------
# Config
# -----------------------
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET")

BLYNK_TOKEN = os.getenv("BLYNK_TOKEN")
ESP32_SECRET = os.getenv("ESP32_SECRET")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

# -----------------------
# Helpers
# -----------------------
def blynk_update(pin, value):
    if isinstance(pin, int):
        pin = f"V{pin}"
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&pin={pin}&value={value}"
    try:
        r = requests.get(url, timeout=3)
        print(f"[DEBUG] blynk_update({pin}) -> {r.text}")
        return r
    except Exception as e:
        print(f"[DEBUG] blynk_update({pin}) error: {e}")
        return None

def _normalize_blynk_value(text):
    text = (text or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed[0] if parsed else None
        return parsed
    except Exception:
        return text

def blynk_get(pin):
    if isinstance(pin, int):
        pin = f"V{pin}"
    url = f"https://blynk.cloud/external/api/get?token={BLYNK_TOKEN}&pin={pin}"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return _normalize_blynk_value(r.text)
    except Exception as e:
        print(f"[DEBUG] blynk_get({pin}) error: {e}, response: {r.text if 'r' in locals() else ''}")
        return None

def google_locate(json_payload):
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
    try:
        r = requests.post(url, json=json_payload, timeout=10)
        r.raise_for_status()
        d = r.json()
        loc = d.get("location", {})
        return {
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "accuracy": d.get("accuracy", 0),
            "mapUrl": f"https://maps.googleapis.com/maps/api/staticmap?center={loc.get('lat')},{loc.get('lng')}&zoom=18&size=400x400&markers=color:red%7C{loc.get('lat')},{loc.get('lng')}&key={GOOGLE_API_KEY}"
        }
    except Exception as e:
        print(f"[DEBUG] google_locate error: {e}, response: {r.text if 'r' in locals() else ''}")
        return None

def parse_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        return int(float(str(value).strip()))
    except Exception:
        return default

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
            print(f"[DEBUG] token decode error: {e}")
            return jsonify({'message': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

# -----------------------
# Routes
# -----------------------
@app.route("/")
def root():
    return send_from_directory('.', 'carlockPWA.html')

# Login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    if data.get('username') == USERNAME and data.get('password') == PASSWORD:
        token = jwt.encode(
            {'user': USERNAME, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)},
            app.config['SECRET_KEY'], algorithm="HS256"
        )
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid credentials'}), 401

# Blynk PIN actions
PIN_MAP = {
    "unlock": "V0",
    "lock": "V1",
    "soundAlarm": "V2",
    "stopAlarm": "V3",
    "flashLights": "V4",
    "stopLights": "V5",
    "remoteStart": "V6",
    "getLocation": "V7"
}

@app.route('/api/<action>', methods=['POST'])
@token_required
def control(action):
    pin = PIN_MAP.get(action)
    if not pin:
        return jsonify({"message": "Invalid action"}), 400

    # For getLocation, pulse so repeated presses still trigger
    if action == "getLocation":
        blynk_update(pin, 1)
        time.sleep(0.2)
        blynk_update(pin, 0)
        return jsonify({"status": "sent", "response": "location trigger pulsed"})

    res = blynk_update(pin, 1)
    return jsonify({"status": "sent", "response": res.text if res else "no response"})

# -----------------------
# Status endpoint for PWA
# -----------------------
@app.route('/api/status', methods=['GET'])
@token_required
def get_status():
    rssi = parse_int(blynk_get("V11"), 0)
    net = parse_int(blynk_get("V13"), 0)
    data = parse_int(blynk_get("V14"), 0)
    engine_running = parse_int(blynk_get("V24"), 0)
    engine_rpm = parse_int(blynk_get("V25"), 0)
    engine_message = blynk_get("V26") or ""

    return jsonify({
        "rssi": rssi,
        "net": 1 if net else 0,
        "data": 1 if data else 0,
        "engineRunning": 1 if engine_running else 0,
        "engineRpm": engine_rpm,
        "engineMessage": str(engine_message)
    })

# -----------------------
# Get car location (V7 -> V8 -> Google)
# -----------------------
@app.route('/api/getCarLocation', methods=['GET'])
@token_required
def get_car_location():
    print("[DEBUG] Triggering V7 scan")

    blynk_update("V7", 1)
    time.sleep(0.2)
    blynk_update("V7", 0)

    scan_json = None
    for i in range(15):
        print(f"[DEBUG] Waiting for V8 data... attempt {i+1}")
        scan_json = blynk_get("V8")
        print(f"[DEBUG] V8 value: {scan_json}")
        if scan_json:
            break
        time.sleep(1)
    else:
        return jsonify({"error": "No scan data from V8"}), 400

    if isinstance(scan_json, str):
        try:
            scan_json = json.loads(scan_json)
        except Exception:
            return jsonify({"error": "Invalid scan data in V8"}), 400

    loc = google_locate(scan_json)
    if not loc:
        return jsonify({"error": "Google geolocation failed"}), 500

    print(f"[DEBUG] Geolocation result: {loc}")
    return jsonify(loc)

# Warmup
@app.route('/api/warmup', methods=['GET'])
@token_required
def warmup():
    return jsonify({"status": "ok"})

# ESP32 Google endpoint
@app.route("/api/location", methods=["POST"])
def api_location():
    auth_header = request.headers.get("Authorization", "")
    if auth_header != f"Bearer {ESP32_SECRET}":
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    return jsonify(google_locate(data))

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
