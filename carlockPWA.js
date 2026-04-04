const API_BASE = "https://carlock-backend-od8a.onrender.com";

window.addEventListener('load', async () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    loadMapFromStorage();
    updateStatus();
    setInterval(updateStatus, 60000);
});

const pending = {};

async function sendCmd(action) {
    const token = localStorage.getItem("token");
    if (!token) return window.location.href = "index.html";

    if (pending[action]) return;
    pending[action] = true;

    try {
        await fetch(`${API_BASE}/api/${action}`, {
            method: "POST",
            headers: { "Authorization": "Bearer " + token }
        });
    } catch (err) {
        console.error(err);
    } finally {
        pending[action] = false;
    }
}

async function updateStatus() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/api/status`, {
            headers: { "Authorization": "Bearer " + token }
        });

        const data = await res.json();
        if (!res.ok) {
            console.error("Status fetch failed:", data);
            return;
        }

        updateLTE(Number(data.rssi || 0));
        updateIndicator("netStatus", Number(data.net || 0));
        updateIndicator("dataStatus", Number(data.data || 0));
        updateEngineStatus({
            engineRunning: Number(data.engineRunning || 0),
            engineRpm: Number(data.engineRpm || 0),
            engineMessage: data.engineMessage || ""
        });
    } catch (e) {
        console.error("Status error", e);
    }
}

function safeNumber(val) {
    if (Array.isArray(val)) val = val[0];
    const num = Number(val);
    return Number.isFinite(num) ? Math.round(num) : 0;
}

function safeBool(val) {
    if (Array.isArray(val)) val = val[0];
    if (typeof val === "boolean") return val ? 1 : 0;
    const text = String(val ?? "").trim().toLowerCase();
    if (["1", "true", "on", "yes", "connected", "online"].includes(text)) return 1;
    if (["0", "false", "off", "no", "disconnected", "offline", ""].includes(text)) return 0;
    const num = Number(text);
    return Number.isFinite(num) && num !== 0 ? 1 : 0;
}

function updateLTE(rssi) {
    document.getElementById("rssiText").innerText = `RSSI: ${rssi}`;

    let bars = 0;
    if (rssi >= 25) bars = 5;
    else if (rssi >= 20) bars = 4;
    else if (rssi >= 15) bars = 3;
    else if (rssi >= 10) bars = 2;
    else if (rssi >= 2) bars = 1;

    const barEls = document.querySelectorAll(".bar");
    barEls.forEach((b, i) => {
        b.style.opacity = i < bars ? 1 : 0.2;
    });
}

function updateIndicator(id, val) {
    const el = document.getElementById(id);
    el.style.background = val ? "limegreen" : "red";
}

async function getLocation() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/api/getCarLocation`, {
            headers: { "Authorization": "Bearer " + token }
        });

        const data = await res.json();

        if (data.mapUrl) {
            localStorage.setItem("lastMapUrl", data.mapUrl);
            document.getElementById("mapThumb").src = data.mapUrl;
        } else {
            console.error("Location data invalid:", data);
            document.getElementById("mapThumb").src = "fallback.png";
        }
    } catch (err) {
        console.error("Failed to fetch car location:", err);
        document.getElementById("mapThumb").src = "fallback.png";
    }
}

function loadMapFromStorage() {
    const url = localStorage.getItem("lastMapUrl");
    document.getElementById("mapThumb").src = url || "fallback.png";
}

document.getElementById("mapThumb").onclick = () => {
    const url = localStorage.getItem("lastMapUrl");
    if (url) window.open(url, "_blank");
};

function logout() {
    localStorage.removeItem("token");
    window.location.href = "index.html";
}


function updateEngineStatus(data) {
    const rpmEl = document.getElementById("engineRpmText");
    const runEl = document.getElementById("engineRunText");
    const msgEl = document.getElementById("engineMsgText");

    const rpm = Number(data.engineRpm || 0);
    const running = Number(data.engineRunning || 0) === 1;
    const message = (data.engineMessage || "").trim();

    rpmEl.innerText = rpm > 0 ? `${rpm} rpm` : "0 rpm";
    runEl.innerText = running ? "Yes" : "No";
    runEl.classList.toggle("engine-running", running);
    runEl.classList.toggle("engine-stopped", !running);
    msgEl.innerText = message || "--";
}
