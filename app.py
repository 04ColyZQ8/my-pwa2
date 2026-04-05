from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests, jwt, datetime, os, json, time
from functools import wraps

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET")

BLYNK_TOKEN = os.getenv("BLYNK_TOKEN")
ESP32_SECRET = os.getenv("ESP32_SECRET")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

APP_OPEN_PIN = "V15"
APP_OPEN_TIMEOUT_SECONDS = 45
app_open_deadline = 0.0
last_app_open_sent = None

_vin_decode_cache = {}


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


def blynk_pulse(pin, active_value=1, idle_value=0, hold_seconds=0.25):
    first = blynk_update(pin, active_value)
    time.sleep(hold_seconds)
    blynk_update(pin, idle_value)
    return first


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
        lat = loc.get('lat')
        lng = loc.get('lng')
        return {
            "lat": lat,
            "lng": lng,
            "accuracy": d.get("accuracy", 0),
            "mapUrl": f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lng}&zoom=18&size=400x400&markers=color:red%7C{lat},{lng}&key={GOOGLE_API_KEY}"
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


def parse_float(value, default=0.0, digits=1):
    try:
        if value is None:
            return default
        return round(float(str(value).strip()), digits)
    except Exception:
        return default


def clean_string(value, default=""):
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


def sync_app_open_state(force=False):
    global app_open_deadline, last_app_open_sent
    desired = 1 if time.time() < app_open_deadline else 0
    if force or last_app_open_sent != desired:
        blynk_update(APP_OPEN_PIN, desired)
        last_app_open_sent = desired
    return desired


def decode_vin_details(vin):
    vin = clean_string(vin, "").upper()
    if len(vin) != 17:
        return None

    cached = _vin_decode_cache.get(vin)
    if cached:
        return cached

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/{vin}?format=json"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        payload = r.json()
        results = payload.get("Results") or []
        row = results[0] if results else {}

        year = clean_string(row.get("ModelYear"))
        make = clean_string(row.get("Make"))
        model = clean_string(row.get("Model"))
        trim = clean_string(row.get("Trim"))

        title_parts = [p for p in [year, make, model] if p]
        title = " ".join(title_parts).strip()
        if trim and trim.lower() not in title.lower():
            title = f"{title} {trim}".strip()

        decoded = {
            "year": year,
            "make": make,
            "model": model,
            "trim": trim,
            "title": title or "Vehicle",
        }
        _vin_decode_cache[vin] = decoded
        return decoded
    except Exception as e:
        print(f"[DEBUG] decode_vin_details({vin}) error: {e}")
        return None


def build_vehicle_title(vin, provided_title):
    provided_title = clean_string(provided_title)
    if provided_title:
        return provided_title
    decoded = decode_vin_details(vin)
    if decoded and decoded.get("title"):
        return decoded["title"]
    return "Vehicle"


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


@app.route("/")
def root():
    return send_from_directory('.', 'carlockPWA.html')


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

    res = blynk_pulse(pin)
    return jsonify({
        "status": "sent",
        "action": action,
        "response": res.text if res else "no response"
    })


@app.route('/api/app-state', methods=['POST'])
@token_required
def app_state():
    global app_open_deadline
    payload = request.get_json(silent=True) or {}
    is_open = bool(payload.get("open", True))

    if is_open:
        app_open_deadline = time.time() + APP_OPEN_TIMEOUT_SECONDS
        state = sync_app_open_state()
    else:
        app_open_deadline = 0
        state = sync_app_open_state(force=True)

    return jsonify({"ok": True, "appOpen": state})


@app.route('/api/status', methods=['GET'])
@token_required
def get_status():
    app_open = sync_app_open_state()

    rssi = parse_int(blynk_get("V11"), 0)
    net = parse_int(blynk_get("V13"), 0)
    data = parse_int(blynk_get("V14"), 0)
    fuel_level = parse_float(blynk_get("V16"), 0.0, 1)
    vehicle_kms = parse_int(blynk_get("V17"), 0)
    vin = clean_string(blynk_get("V18"), "")
    vehicle_title = build_vehicle_title(vin, blynk_get("V19"))
    door_unlocked = parse_int(blynk_get("V20"), 0)
    engine_running = parse_int(blynk_get("V24"), 0)
    engine_rpm = parse_int(blynk_get("V25"), 0)
    engine_message = clean_string(blynk_get("V26"), "Ready")
    lock_message = clean_string(blynk_get("V27"), "Ready")

    return jsonify({
        "appOpen": app_open,
        "rssi": rssi,
        "net": 1 if net else 0,
        "data": 1 if data else 0,
        "fuelLevel": fuel_level,
        "vehicleKms": vehicle_kms,
        "vin": vin,
        "vehicleTitle": vehicle_title,
        "doorUnlocked": 1 if door_unlocked else 0,
        "engineRunning": 1 if engine_running else 0,
        "engineRpm": engine_rpm,
        "engineMessage": engine_message,
        "lockMessage": lock_message
    })


@app.route('/api/getCarLocation', methods=['GET'])
@token_required
def get_car_location():
    print("[DEBUG] Triggering V7 scan")

    blynk_pulse("V7")

    scan_json = None
    for i in range(15):
        print(f"[DEBUG] Waiting for V8 data... attempt {i + 1}")
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


@app.route('/api/warmup', methods=['GET'])
@token_required
def warmup():
    return jsonify({"status": "ok"})


@app.route("/api/location", methods=["POST"])
def api_location():
    auth_header = request.headers.get("Authorization", "")
    if auth_header != f"Bearer {ESP32_SECRET}":
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    return jsonify(google_locate(data))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
