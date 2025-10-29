from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import jwt, datetime, requests
from functools import wraps

app = Flask(__name__, static_folder='static', static_url_path='/')
CORS(app)

app.config['SECRET_KEY'] = 'supersecretkey'  # Change this for real use

# Example "database" (can later replace with real DB)
USERS = {
    "jake": {
        "password": "mypassword",
        "blynk_token": "LcIEIHmUOMbwC8xi-3Au3CQM7lNajKR9"
    },
    "demo": {
        "password": "1234",
        "blynk_token": "AnotherCarBlynkToken"
    }
}

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token missing'}), 401
        try:
            token = token.replace("Bearer ", "")
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            request.user = data['user']
        except Exception as e:
            return jsonify({'message': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username, password, car_token = data.get("username"), data.get("password"), data.get("blynk_token")
    if username in USERS:
        return jsonify({"message": "User already exists"}), 400
    USERS[username] = {"password": password, "blynk_token": car_token}
    return jsonify({"message": "User registered successfully"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username, password = data.get("username"), data.get("password")
    user = USERS.get(username)
    if not user or user["password"] != password:
        return jsonify({"message": "Invalid credentials"}), 401

    token = jwt.encode({
        'user': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'token': token})

def blynk_update(user, pin, value):
    token = USERS[user]["blynk_token"]
    url = f"https://blynk.cloud/external/api/update?token={token}&pin={pin}&value={value}"
    return requests.get(url)

@app.route("/api/unlock", methods=["POST"])
@token_required
def unlock():
    res = blynk_update(request.user, "V0", 1)
    return jsonify({"status": "sent", "response": res.text})

@app.route("/api/lock", methods=["POST"])
@token_required
def lock():
    res = blynk_update(request.user, "V4", 1)
    return jsonify({"status": "sent", "response": res.text})

@app.route("/api/status", methods=["GET"])
@token_required
def status():
    token = USERS[request.user]["blynk_token"]
    url = f"https://blynk.cloud/external/api/get?token={token}&pin=V0"
    res = requests.get(url)
    return jsonify(res.json())

@app.route("/")
def serve_login():
    return send_from_directory('static', 'login.html')

@app.route("/dashboard")
def serve_dashboard():
    return send_from_directory('static', 'carlockPWA.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
