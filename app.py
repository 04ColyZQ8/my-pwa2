from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import jwt
import datetime
from functools import wraps

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# -----------------------
# Config
# -----------------------
app.config['SECRET_KEY'] = 'supersecretkey'  # Change this!
BLYNK_TOKEN = "LcIEIHmUOMbwC8xi-3Au3CQM7lNajKR9"
USERNAME = "youruser"
PASSWORD = "yourpass"

# -----------------------
# Helpers
# -----------------------
def blynk_update(pin, value):
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&pin={pin}&value={value}"
    return requests.get(url)

# -----------------------
# JWT Auth
# -----------------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            token = token.replace("Bearer ", "")
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return jsonify({'message': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if username == USERNAME and password == PASSWORD:
        token = jwt.encode(
            {'user': username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)},
            app.config['SECRET_KEY'], algorithm="HS256"
        )
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid credentials'}), 401

# -----------------------
# PWA Endpoints
# -----------------------
@app.route("/")
def root():
    return send_from_directory('.', 'carlockPWA.html')

@app.route("/api/unlock", methods=["POST"])
@token_required
def unlock():
    res = blynk_update("V0", 1)
    return jsonify({"status": "sent", "response": res.text})

@app.route("/api/lock", methods=["POST"])
@token_required
def lock():
    res = blynk_update("V4", 1)
    return jsonify({"status": "sent", "response": res.text})

@app.route("/api/status", methods=["GET"])
@token_required
def status():
    url = f"https://blynk.cloud/external/api/get?token={BLYNK_TOKEN}&pin=V0"
    res = requests.get(url)
    return jsonify(res.json())

# -----------------------
# Run Server
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
