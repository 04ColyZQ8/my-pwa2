from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests, jwt, datetime, os, json
from functools import wraps

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# -----------------------
# Config
# -----------------------
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET", "supersecretkey")
BLYNK_TOKEN = os.getenv("BLYNK_TOKEN", "LcIEIHmUOMbwC8xi-3Au3CQM7lNajKR9")
ESP32_SECRET = os.getenv("ESP32_SECRET", "MY_SUPER_SECRET_1234567890")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

USERNAME = os.getenv("USERNAME", "Jamie")
PASSWORD = os.getenv("PASSWORD", "trax123")

# -----------------------
# Helpers
# -----------------------
def blynk_update(pin, value):
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&pin={pin}&value={value}"
    try:
        return requests.get(url, timeout=3)
    except:
        return None

def blynk_get(pin):
    url = f"https://blynk.cloud/external/api/get?token={BLYNK_TOKEN}&v{pin}"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return None

def google_locate(json_payload):
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
    r = requests.post(url, json=json_payload)
    if r.status_code != 200:
        return None
    d = r.json()
    loc = d.get("location", {})
    return {
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
        "accuracy": d.get("accuracy", 0),
        "mapUrl": f"https://www.google.com/maps?q={loc.get('lat')},{loc.get('lng')}&z=18"
    }

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
        except:
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
    data = request.json
    if data and data.get('username') == USERNAME and data.get('password') == PASSWORD:
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
    res = blynk_update(pin, 1)
    return jsonify({"status": "sent", "response": res.text if res else "no response"})

# NEW: Fetch location via Blynk V8
@app.route('/api/getCarLocation', methods=['GET'])
@token_required
def get_car_location():
    scan_json = blynk_get(8)  # V8
    if not scan_json:
        return jsonify({"error": "No scan data"}), 400

    loc = google_locate(scan_json)
    if not loc:
        return jsonify({"error": "Google failed"}), 500

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
