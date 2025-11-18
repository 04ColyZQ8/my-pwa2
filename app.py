from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests, jwt, datetime, os, json, time
from functools import wraps

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# -----------------------
# Config
# -----------------------
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET", "supersecretkey")
BLYNK_TOKEN = os.getenv("BLYNK_TOKEN", "REPLACE_ME")
ESP32_SECRET = os.getenv("ESP32_SECRET", "MY_SUPER_SECRET_1234567890")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

USERNAME = os.getenv("USERNAME", "Jamie")
PASSWORD = os.getenv("PASSWORD", "trax123")

# -----------------------
# Helpers
# -----------------------

def blynk_update(pin, value):
    """Send update to Blynk Vpin"""
    if isinstance(pin, int):
        pin = f"V{pin}"
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&pin={pin}&value={value}"

    print(f"[DEBUG] blynk_update URL = {url}")

    try:
        r = requests.get(url, timeout=4)
        print(f"[DEBUG] Blynk update response = {r.text}")
        return r
    except Exception as e:
        print(f"[DEBUG] update error: {e}")
        return None


def blynk_get(pin):
    """Correct Blynk GET format is: ?token=XXX&pin=V8"""
    pin_name = f"V{pin}"
    url = f"https://blynk.cloud/external/api/get?token={BLYNK_TOKEN}&pin={pin_name}"

    print(f"[DEBUG] blynk_get URL = {url}")

    try:
        r = requests.get(url, timeout=4)
        print(f"[DEBUG] blynk_get raw response = {r.text}")

        if not r.text:
            return None

        text = r.text.strip()

        # Blynk returns something like: {"bssid":"xx","wifi":[...]}
        # or returns direct JSON
        try:
            return json.loads(text)
        except:
            print("[DEBUG] JSON decode failed")
            return None

    except Exception as e:
        print(f"[DEBUG] GET error: {e}")
        return None


def google_locate(json_payload):
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
    print("[DEBUG] Sending to Google:", json_payload)

    try:
        r = requests.post(url, json=json_payload, timeout=10)
        print("[DEBUG] Google Response:", r.text)
        r.raise_for_status()

        d = r.json()
        loc = d.get("location", {})

        return {
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "accuracy": d.get("accuracy", 0),
            "mapUrl": f"https://www.google.com/maps?q={loc.get('lat')},{loc.get('lng')}&z=18"
        }

    except Exception as e:
        print(f"[DEBUG] google error: {e}")
        return None

# -----------------------
# JWT Auth
# -----------------------

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"message": "Missing token"}), 401

        token = token.replace("Bearer ", "")

        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except Exception as e:
            print(f"[DEBUG] JWT decode failed: {e}")
            return jsonify({"message": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated

# -----------------------
# Routes
# -----------------------

@app.route("/")
def root():
    return send_from_directory(".", "carlockPWA.html")

# Login
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json

    if data.get("username") == USERNAME and data.get("password") == PASSWORD:
        token = jwt.encode(
            {"user": USERNAME,
             "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)},
            app.config["SECRET_KEY"],
            algorithm="HS256"
        )
        return jsonify({"token": token})

    return jsonify({"message": "Invalid credentials"}), 401


# Blynk control buttons
PIN_MAP = {
    "unlock": 0,
    "lock": 1,
    "soundAlarm": 2,
    "stopAlarm": 3,
    "flashLights": 4,
    "stopLights": 5,
    "remoteStart": 6,
    "getLocation": 7
}

@app.route("/api/<action>", methods=["POST"])
@token_required
def control(action):
    if action not in PIN_MAP:
        return jsonify({"message": "Invalid action"}), 400

    pin = PIN_MAP[action]

    r = blynk_update(pin, 1)
    time.sleep(0.2)
    blynk_update(pin, 0)

    return jsonify({"status": "sent", "response": r.text if r else "none"})

# -----------------------
# Car Location Logic
# -----------------------

@app.route("/api/getCarLocation", methods=["GET"])
@token_required
def get_car_location():

    print("\n========== START LOCATION REQUEST ========== ")

    # 1) Pulse V7 for ESP32 scan
    print("[DEBUG] Pulsing V7")
    blynk_update(7, 1)
    time.sleep(0.2)
    blynk_update(7, 0)

    # 2) Poll V8 for scan JSON
    scan_data = None
    for attempt in range(12):
        print(f"[DEBUG] Checking V8... ({attempt+1}/12)")
        scan_data = blynk_get(8)

        if scan_data:
            print("[DEBUG] Got V8:", scan_data)
            break

        time.sleep(1)

    if not scan_data:
        return jsonify({"error": "No scan data received on V8"}), 400

    # 3) Send to Google API
    loc = google_locate(scan_data)

    if not loc:
        return jsonify({"error": "Google geolocation error"}), 500

    print("[DEBUG] FINAL LOCATION:", loc)
    print("============================================\n")

    return jsonify(loc)

# -----------------------
# Warmup
# -----------------------

@app.route("/api/warmup", methods=["GET"])
@token_required
def warmup():
    return jsonify({"status": "ok"})

# -----------------------
# ESP32 direct Google endpoint
# -----------------------

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
