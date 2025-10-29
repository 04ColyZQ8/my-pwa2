from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, jwt, datetime
from functools import wraps

app = Flask(__name__)
CORS(app)

# -----------------------
# Config
# -----------------------
app.config['SECRET_KEY'] = 'supersecretkey'  # change this
BLYNK_TOKEN = "LcIEIHmUOMbwC8xi-3Au3CQM7lNajKR9"
USERNAME = "youruser"    # change as needed
PASSWORD = "yourpass"

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
    res = blynk_update("V4", 1)
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
    """Ping all pins to avoid first-click delay"""
    pins = ["V0", "V1", "V2", "V3", "V4", "V5"]
    for pin in pins:
        blynk_update(pin, 0)
    return jsonify({"status": "warmed up"})

# -----------------------
# Run Server
# -----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
