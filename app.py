from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests, jwt, datetime, os
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

def get_location(data):
    google_url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
    response = requests.post(google_url, json=data)
    if response.status_code == 200:
        geo = response.json()
        loc = geo.get("location", {})
        return {
            "lat": loc.get("lat", 0),
            "lng": loc.get("lng", 0),
            "accuracy": geo.get("accuracy", 0)
        }
    else:
        return {"error": response.text}, response.status_code

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

# JWT login
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

# JWT-controlled actions
PIN_MAP = {
    "unlock": "V0",
    "lock": "V1",
    "soundAlarm": "V2",
    "stopAlarm": "V3",
    "flashLights": "V4",
    "stopLights": "V5",
    "remoteStart": "V6"
}

@app.route('/api/<action>', methods=['POST'])
@token_required
def control(action):
    pin = PIN_MAP.get(action)
    if not pin:
        return jsonify({"message": "Invalid action"}), 400
    res = blynk_update(pin, 1)
    return jsonify({"status": "sent", "response": res.text if res else "dummy response"})

@app.route('/api/status', methods=['GET'])
@token_required
def status():
    response = {}
    for action, pin in PIN_MAP.items():
        try:
            res = requests.get(f"https://blynk.cloud/external/api/get?token={BLYNK_TOKEN}&pin={pin}", timeout=2)
            response[pin] = int(res.text) if res else 0
        except:
            response[pin] = 0
    return jsonify(response)

@app.route('/api/warmup', methods=['GET'])
@token_required
def warmup():
    for pin in PIN_MAP.values():
        blynk_update(pin, 0)
    return jsonify({"status": "warmed up"})

# ESP32-friendly location endpoint
@app.route("/api/location", methods=["POST"])
def api_location():
    auth_header = request.headers.get("Authorization", "")
    if auth_header != f"Bearer {ESP32_SECRET}":
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    return jsonify(get_location(data))

# -----------------------
# Run server
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
