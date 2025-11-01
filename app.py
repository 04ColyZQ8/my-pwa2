from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, jwt, datetime
from functools import wraps

app = Flask(__name__)
CORS(app)

# -----------------------
# Config
# -----------------------
app.config['SECRET_KEY'] = 'supersecretkey'  # change as needed
BLYNK_TOKEN = "LcIEIHmUOMbwC8xi-3Au3CQM7lNajKR9"
USERNAME = "Jamie"
PASSWORD = "trax123"

# -----------------------
# Helpers
# -----------------------
def blynk_update(pin, value):
    """Send a command to Blynk cloud"""
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&pin={pin}&value={value}"
    try:
        res = requests.get(url, timeout=3)
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
        except:
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
# Control Endpoints (unique pins!)
# -----------------------
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

# -----------------------
# Status Endpoint
# -----------------------
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

# -----------------------
# Warmup Endpoint
# -----------------------
@app.route('/api/warmup', methods=['GET'])
@token_required
def warmup():
    for pin in PIN_MAP.values():
        blynk_update(pin, 0)
    return jsonify({"status": "warmed up"})

# -----------------------
# Run Server
# -----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
