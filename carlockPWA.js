const API_BASE = "https://carlock-backend-od8a.onrender.com";
const STATUS_POLL_MS = 2000;
const APP_HEARTBEAT_MS = 15000;

const pending = {};
let statusTimer = null;
let heartbeatTimer = null;
let statusFetchInFlight = false;
let appVisible = false;

window.addEventListener('load', async () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "index.html";
        return;
    }

    loadMapFromStorage();
    document.getElementById("mapThumb").onclick = () => {
        const url = localStorage.getItem("lastMapUrl");
        if (url) window.open(url, "_blank");
    };

    handleVisibilityChange();
});

document.addEventListener("visibilitychange", handleVisibilityChange);
window.addEventListener("focus", handleVisibilityChange);
window.addEventListener("blur", handleVisibilityChange);
window.addEventListener("pagehide", () => notifyAppState(false, true));
window.addEventListener("beforeunload", () => notifyAppState(false, true));

function isAppVisible() {
    return document.visibilityState === "visible" && document.hasFocus();
}

function handleVisibilityChange() {
    const visibleNow = isAppVisible();
    if (visibleNow === appVisible && statusTimer && heartbeatTimer) {
        return;
    }

    appVisible = visibleNow;

    if (appVisible) {
        notifyAppState(true);
        updateStatus();
        startStatusPolling();
        startHeartbeat();
    } else {
        stopStatusPolling();
        stopHeartbeat();
        notifyAppState(false, true);
    }
}

function startStatusPolling() {
    stopStatusPolling();
    statusTimer = setInterval(updateStatus, STATUS_POLL_MS);
}

function stopStatusPolling() {
    if (statusTimer) {
        clearInterval(statusTimer);
        statusTimer = null;
    }
}

function startHeartbeat() {
    stopHeartbeat();
    heartbeatTimer = setInterval(() => notifyAppState(true), APP_HEARTBEAT_MS);
}

function stopHeartbeat() {
    if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
    }
}

async function notifyAppState(open, useBeacon = false) {
    const token = localStorage.getItem("token");
    if (!token) return;

    const url = `${API_BASE}/api/app-state`;
    const body = JSON.stringify({ open });

    if (useBeacon && navigator.sendBeacon) {
        const blob = new Blob([body], { type: "application/json" });
        fetch(url, {
            method: "POST",
            headers: {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json"
            },
            body,
            keepalive: true
        }).catch(() => {});
        try {
            navigator.sendBeacon(url, blob);
        } catch (_) {}
        return;
    }

    try {
        await fetch(url, {
            method: "POST",
            headers: {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json"
            },
            body,
            keepalive: true
        });
    } catch (err) {
        console.error("App state update failed", err);
    }
}

function setLockMessage(message) {
    const el = document.getElementById("lockMessageText");
    if (el) el.innerText = message || "Ready";
}

async function sendCmd(action) {
    const token = localStorage.getItem("token");
    if (!token) return window.location.href = "index.html";

    if (pending[action]) return;
    pending[action] = true;

    if (action === "lock") setLockMessage("Lock request sent...");
    if (action === "unlock") setLockMessage("Unlock request sent...");

    try {
        const res = await fetch(`${API_BASE}/api/${action}`, {
            method: "POST",
            headers: { "Authorization": "Bearer " + token }
        });

        if (!res.ok) {
            console.error(`Command ${action} failed`, await res.text());
        }

        setTimeout(updateStatus, 400);
        setTimeout(updateStatus, 1500);
        setTimeout(updateStatus, 3000);
    } catch (err) {
        console.error(err);
        if (action === "lock" || action === "unlock") {
            setLockMessage("Command send failed");
        }
    } finally {
        pending[action] = false;
    }
}

async function updateStatus() {
    const token = localStorage.getItem("token");
    if (!token || !appVisible || statusFetchInFlight) return;

    statusFetchInFlight = true;

    try {
        const res = await fetch(`${API_BASE}/api/status`, {
            headers: { "Authorization": "Bearer " + token },
            cache: "no-store"
        });

        const data = await res.json();
        if (!res.ok) {
            console.error("Status fetch failed:", data);
            return;
        }

        updateVehicleMeta(data);
        updateLTE(Number(data.rssi || 0));
        updateIndicator("netStatus", Number(data.net || 0));
        updateIndicator("dataStatus", Number(data.data || 0));
        updateEngineStatus(
            Number(data.engineRunning || 0),
            Number(data.engineRpm || 0),
            data.engineMessage || "Ready"
        );
        setLockMessage(data.lockMessage || "Ready");
    } catch (e) {
        console.error("Status error", e);
    } finally {
        statusFetchInFlight = false;
    }
}

function updateVehicleMeta(data) {
    const titleEl = document.getElementById("vehicleTitle");
    const statsEl = document.getElementById("vehicleStats");
    const vinEl = document.getElementById("vehicleVin");

    if (titleEl) {
        titleEl.innerText = data.vehicleTitle || "Vehicle";
    }

    if (statsEl) {
        const fuelText = Number.isFinite(Number(data.fuelLevel)) ? `${Number(data.fuelLevel).toFixed(1)}%` : "--";
        const kmText = Number(data.vehicleKms || 0) > 0 ? `${Number(data.vehicleKms).toLocaleString()} km` : "-- km";
        statsEl.innerText = `Fuel: ${fuelText} · ${kmText}`;
    }

    if (vinEl) {
        vinEl.innerText = `VIN: ${data.vin || '--'}`;
    }
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
    if (el) el.style.background = val ? "limegreen" : "red";
}

function updateEngineStatus(running, rpm, message) {
    const rpmEl = document.getElementById("engineRpmText");
    const runningEl = document.getElementById("engineRunningText");
    const msgEl = document.getElementById("engineMessageText");

    if (rpmEl) rpmEl.innerText = rpm > 0 ? String(rpm) : "--";
    if (msgEl) msgEl.innerText = message || "Ready";

    if (runningEl) {
        runningEl.innerText = running ? "RUNNING" : "OFF";
        runningEl.classList.remove("on", "off");
        runningEl.classList.add(running ? "on" : "off");
    }
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

function logout() {
    notifyAppState(false, true);
    localStorage.removeItem("token");
    window.location.href = "index.html";
}
