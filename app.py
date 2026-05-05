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

VIN_CACHE = {}
VIN_CACHE_TTL_SECONDS = 12 * 60 * 60


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


def blynk_pulse(pin, high_value=1, low_value=0, hold_seconds=0.20):
    r1 = blynk_update(pin, high_value)
    time.sleep(hold_seconds)
    r0 = blynk_update(pin, low_value)
    return r0 or r1


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
        return build_map_result(loc.get("lat"), loc.get("lng"), d.get("accuracy", 0), "wifi")
    except Exception as e:
        print(f"[DEBUG] google_locate error: {e}, response: {r.text if 'r' in locals() else ''}")
        return None


def coords_look_sane(lat, lng):
    try:
        lat = float(lat)
        lng = float(lng)
    except Exception:
        return False
    if lat == 0 and lng == 0:
        return False
    return -90 <= lat <= 90 and -180 <= lng <= 180


def build_map_result(lat, lng, accuracy=0, source="onstar", extra=None):
    if not coords_look_sane(lat, lng):
        return None
    lat = float(lat)
    lng = float(lng)
    result = {
        "lat": lat,
        "lng": lng,
        "accuracy": accuracy or 0,
        "source": source,
        "googleMapsUrl": f"https://www.google.com/maps?q={lat:.6f},{lng:.6f}",
        "mapUrl": (
            "https://maps.googleapis.com/maps/api/staticmap"
            f"?center={lat:.6f},{lng:.6f}"
            "&zoom=18&size=400x400"
            f"&markers=color:red%7C{lat:.6f},{lng:.6f}"
            f"&key={GOOGLE_API_KEY}"
        )
    }
    if isinstance(extra, dict):
        result.update(extra)
    return result


def parse_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        return int(float(str(value).strip()))
    except Exception:
        return default


def parse_float(value, default=0.0):
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return float(value)
        return float(str(value).strip())
    except Exception:
        return default


def clean_text(value, default=""):
    value = "" if value is None else str(value).strip()
    return value or default


def sync_app_open_state(force=False):
    global app_open_deadline, last_app_open_sent
    desired = 1 if time.time() < app_open_deadline else 0
    if force or last_app_open_sent != desired:
        blynk_update(APP_OPEN_PIN, desired)
        last_app_open_sent = desired
    return desired


def infer_year_from_vin(vin):
    vin = clean_text(vin).upper()
    if len(vin) != 17:
        return None
    code = vin[9]
    codes = "ABCDEFGHJKLMNPRSTVWXY123456789"
    idx = codes.find(code)
    if idx < 0:
        return None
    return 2010 + idx


def decode_vin_nhtsa(vin):
    vin = clean_text(vin).upper()
    if len(vin) != 17:
        return None

    now = time.time()
    cached = VIN_CACHE.get(vin)
    if cached and (now - cached["ts"] < VIN_CACHE_TTL_SECONDS):
        return cached["data"]

    year = infer_year_from_vin(vin)
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/{vin}?format=json"
    if year:
        url += f"&modelyear={year}"

    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        rows = r.json().get("Results", [])
        if not rows:
            return None

        row = rows[0]
        decoded = {
            "year": clean_text(row.get("ModelYear"), str(year or "")),
            "make": clean_text(row.get("Make")),
            "model": clean_text(row.get("Model")),
        }

        if not decoded["year"] and year:
            decoded["year"] = str(year)

        if not decoded["make"] and not decoded["model"] and not decoded["year"]:
            return None

        VIN_CACHE[vin] = {"ts": now, "data": decoded}
        return decoded
    except Exception as e:
        print(f"[DEBUG] decode_vin_nhtsa error for {vin}: {e}")
        return None


def compose_vehicle_name(vin, fallback_text="Vehicle"):
    decoded = decode_vin_nhtsa(vin)
    if decoded:
        parts = [decoded.get("year"), decoded.get("make"), decoded.get("model")]
        text = " ".join(p for p in parts if p)
        if text.strip():
            return text.strip()
    return clean_text(fallback_text, "Vehicle")


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
    return jsonify({"status": "sent", "response": res.text if res else "no response"})


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

    vin = clean_text(blynk_get("V18"))
    fallback_vehicle_name = clean_text(blynk_get("V19"), "Vehicle")
    vehicle_name = compose_vehicle_name(vin, fallback_vehicle_name)

    return jsonify({
        "appOpen": app_open,
        "rssi": parse_int(blynk_get("V11"), 0),
        "net": 1 if parse_int(blynk_get("V13"), 0) else 0,
        "data": 1 if parse_int(blynk_get("V14"), 0) else 0,
        "fuelPct": parse_float(blynk_get("V16"), 0.0),
        "odometerKm": parse_int(blynk_get("V17"), 0),
        "vin": vin,
        "vehicleName": vehicle_name,
        "lockMessage": clean_text(blynk_get("V27"), "Ready"),
        "engineRunning": 1 if parse_int(blynk_get("V24"), 0) else 0,
        "engineRpm": parse_int(blynk_get("V25"), 0),
        "engineMessage": clean_text(blynk_get("V26"), "Ready"),
        "gpsLat": parse_float(blynk_get("V28"), 0.0),
        "gpsLng": parse_float(blynk_get("V29"), 0.0),
        "gpsStatus": clean_text(blynk_get("V30"), "GPS unavailable"),
        "gpsSpeedKmh": parse_int(blynk_get("V31"), 0),
        "gpsHeading": parse_int(blynk_get("V32"), 0)
    })


@app.route('/api/getCarLocation', methods=['GET'])
@token_required
def get_car_location():
    print("[DEBUG] Triggering V7 location request - OnStar GPS only")

    # Ask ESP32 to wake the bus and refresh OnStar GPS.
    # IMPORTANT: do NOT use Google Wi-Fi geolocation fallback here. It produced bad
    # cached/remote coordinates in testing. Only accept V28/V29 from OnStar CAN GPS.
    blynk_pulse("V7")

    loc = None
    for i in range(8):
        lat = parse_float(blynk_get("V28"), 0.0)
        lng = parse_float(blynk_get("V29"), 0.0)
        gps_status = clean_text(blynk_get("V30"), "OnStar GPS")
        speed = parse_int(blynk_get("V31"), 0)
        heading = parse_int(blynk_get("V32"), 0)

        print(f"[DEBUG] OnStar GPS attempt {i+1}: lat={lat}, lng={lng}, status={gps_status}")

        if coords_look_sane(lat, lng):
            loc = build_map_result(
                lat,
                lng,
                10,
                "OnStar GPS",
                {
                    "gpsStatus": gps_status,
                    "speedKmh": speed,
                    "heading": heading,
                }
            )
            break

        time.sleep(1)

    if loc:
        print(f"[DEBUG] OnStar vehicle location result: {loc}")
        return jsonify(loc)

    return jsonify({
        "error": "onstar_gps_not_ready",
        "message": "OnStar GPS not ready yet. Try again in a second. Wi-Fi fallback is disabled to avoid bad coordinates."
    }), 202


@app.route('/api/warmup', methods=['GET'])
@token_required
def warmup():
    return jsonify({"status": "ok"})


@app.route("/api/location", methods=["POST"])
def api_location():
    auth_header = request.headers.get("Authorization", "")
    if auth_header != f"Bearer {ESP32_SECRET}":
        return jsonify({"error": "Unauthorized"}), 401

    # Legacy ESP32 Wi-Fi geolocation endpoint intentionally disabled.
    # Location now comes from OnStar GPS via Blynk V28/V29 only.
    return jsonify({
        "error": "wifi_geolocation_disabled",
        "message": "Use /api/getCarLocation; OnStar GPS only."
    }), 410


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
