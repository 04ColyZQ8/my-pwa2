from flask import Flask, request, jsonify, send_from_directory
import requests
from flask_cors import CORS
import jwt
import datetime

app = Flask(__name__, static_folder='.')
CORS(app)

SECRET = "your_secret_key"
BLYNK_TOKEN = "LcIEIHmUOMbwC8xi-3Au3CQM7lNajKR9"

# =========================
# AUTH
# =========================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    if data["username"] == "admin" and data["password"] == "password":
        token = jwt.encode({
            "user": data["username"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, SECRET, algorithm="HS256")
        return jsonify({"token": token})
    return jsonify({"message": "Invalid login"}), 401


def verify_token(req):
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        jwt.decode(token, SECRET, algorithms=["HS256"])
        return True
    except:
        return False


# =========================
# BLYNK HELPERS (FIXED)
# =========================
def blynk_write(pin, value):
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&{pin}={value}"
    requests.get(url)


def blynk_get(pin):
    url = f"https://blynk.cloud/external/api/get?token={BLYNK_TOKEN}&pin={pin}"
    r = requests.get(url)

    if r.status_code != 200:
        return None

    try:
        data = r.json()
        if isinstance(data, list):
            return data[0]
        return data
    except:
        return r.text


# =========================
# COMMAND ROUTES
# =========================
@app.route("/api/<action>", methods=["POST"])
def send_action(action):
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    mapping = {
        "unlock": ("V0", 1),
        "lock": ("V1", 1),
        "soundAlarm": ("V2", 1),
        "stopAlarm": ("V3", 1),
        "flashLights": ("V4", 1),
        "stopLights": ("V5", 1),
        "remoteStart": ("V6", 1),
        "getLocation": ("V7", 1),
    }

    if action in mapping:
        pin, val = mapping[action]
        blynk_write(pin, val)
        return jsonify({"status": "ok"})

    return jsonify({"error": "invalid command"}), 400


# =========================
# STATUS ENDPOINT (NEW)
# =========================
@app.route("/api/status")
def status():
    try:
        return jsonify({
            "rssi": int(blynk_get("V11") or 0),
            "net": int(blynk_get("V13") or 0),
            "data": int(blynk_get("V14") or 0)
        })
    except:
        return jsonify({"error": "failed"}), 500


# =========================
# LOCATION
# =========================
@app.route("/api/getCarLocation")
def get_location():
    return jsonify({"mapUrl": None})


# =========================
# STATIC FILES
# =========================
@app.route("/")
def root():
    return send_from_directory(".", "carlockPWA.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


if __name__ == "__main__":
    app.run(debug=True)