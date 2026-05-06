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
        const url = localStorage.getItem("lastGoogleMapsUrl") || localStorage.getItem("lastMapUrl");
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

        setTimeout(updateStatus, 400);
        setTimeout(updateStatus, 1500);
    } catch (err) {
        console.error(err);
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

        updateLTE(Number(data.rssi || 0));
        updateIndicator("netStatus", Number(data.net || 0));
        updateIndicator("dataStatus", Number(data.data || 0));
        updateVehicleHeader(data);
        updateEngineStatus(
            Number(data.engineRunning || 0),
            Number(data.engineRpm || 0),
            data.engineMessage || "Ready"
        );
        updateGpsStatus(data);
    } catch (e) {
        console.error("Status error", e);
    } finally {
        statusFetchInFlight = false;
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

function formatKm(km) {
    const num = Number(km || 0);
    return num.toLocaleString("en-CA");
}

function getCachedVehicleInfo() {
    try {
        return JSON.parse(localStorage.getItem("vehicleInfoCache") || "{}");
    } catch (_) {
        return {};
    }
}

function saveVehicleInfoCache(info) {
    const current = getCachedVehicleInfo();
    const next = Object.assign({}, current, info, { ts: Date.now() });
    localStorage.setItem("vehicleInfoCache", JSON.stringify(next));
}

function updateVehicleHeader(data) {
    const vehicleNameEl = document.getElementById("vehicleNameText");
    const vehicleStatsEl = document.getElementById("vehicleStatsText");
    const vinEl = document.getElementById("vehicleVinText");
    const lockEl = document.getElementById("lockMessageText");

    const cached = getCachedVehicleInfo();
    const fuel = Math.round(Number(data.fuelPct || 0));
    const km = Number(data.odometerKm || 0);
    const vin = data.vin || cached.vin || "--";
    let vehicleName = data.vehicleName || cached.vehicleName || "Vehicle";
    if ((!data.vehicleName || data.vehicleName === "Vehicle") && cached.vehicleName) {
        vehicleName = cached.vehicleName;
    }
    const lockMessage = data.lockMessage || "Ready";

    if (vin && vin !== "--") {
        saveVehicleInfoCache({ vin, vehicleName });
    }

    if (vehicleNameEl) vehicleNameEl.innerText = vehicleName;
    if (vehicleStatsEl) vehicleStatsEl.innerText = `Fuel: ${fuel}% · ${formatKm(km)} km`;
    if (vinEl) vinEl.innerText = `VIN: ${vin}`;
    if (lockEl) {
        lockEl.innerText = lockMessage;
        lockEl.classList.remove("ok", "warn", "fail");

        const msg = lockMessage.toLowerCase();
        if (msg.includes("success")) lockEl.classList.add("ok");
        else if (msg.includes("fail")) lockEl.classList.add("fail");
        else if (msg.includes("sent")) lockEl.classList.add("warn");
    }
}

function updateGpsStatus(data) {
    const el = document.getElementById("gpsStatusText");
    if (!el) return;

    const lat = Number(data.gpsLat || 0);
    const lng = Number(data.gpsLng || 0);
    const source = data.gpsStatus || "GPS unavailable";
    const speed = Number(data.gpsSpeedKmh || 0);
    const heading = Number(data.gpsHeading || 0);

    if (lat && lng) {
        el.innerText = `GPS: ${source} · ${lat.toFixed(5)}, ${lng.toFixed(5)} · ${speed} km/h · ${heading}°`;
    } else {
        el.innerText = `GPS: ${source}`;
    }
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

async function getLocation(retryCount = 0) {
    const token = localStorage.getItem("token");
    if (!token) return;

    const map = document.getElementById("mapThumb");
    const info = document.getElementById("mapInfoText");

    // Prevent stale bad Wi-Fi/cached maps from displaying while OnStar wakes up.
    if (retryCount === 0) {
        localStorage.removeItem("lastMapUrl");
        localStorage.removeItem("lastGoogleMapsUrl");
        if (info) info.innerText = "Getting OnStar GPS...";
    }

    try {
        const res = await fetch(`${API_BASE}/api/getCarLocation`, {
            headers: { "Authorization": "Bearer " + token },
            cache: "no-store"
        });

        const data = await res.json();

        if (res.status === 202 && retryCount < 4) {
            if (info) info.innerText = `Waiting for OnStar GPS... ${retryCount + 1}/4`;
            setTimeout(() => getLocation(retryCount + 1), 1500);
            return;
        }

        if (data.mapUrl) {
            localStorage.setItem("lastMapUrl", data.mapUrl);
            if (data.googleMapsUrl) localStorage.setItem("lastGoogleMapsUrl", data.googleMapsUrl);
            if (map) map.src = data.mapUrl;
            if (info) {
                const source = data.source || "OnStar GPS";
                const lat = Number(data.lat || 0);
                const lng = Number(data.lng || 0);
                const speed = Number(data.speedKmh || 0);
                const heading = Number(data.heading || 0);
                info.innerText = `${source} · ${lat.toFixed(6)}, ${lng.toFixed(6)} · ${speed} km/h · heading ${heading}°`;
            }
        } else {
            console.error("Location data invalid:", data);
            if (info) info.innerText = data.message || "OnStar GPS not ready";
            if (map) map.src = "fallback.png";
        }
    } catch (err) {
        console.error("Failed to fetch car location:", err);
        if (info) info.innerText = "Location request failed";
        if (map) map.src = "fallback.png";
    }
}

function loadMapFromStorage() {
    const url = localStorage.getItem("lastMapUrl");
    document.getElementById("mapThumb").src = url || "fallback.png";
    const info = document.getElementById("mapInfoText");
    if (info && url) info.innerText = "Last known location";
}

function logout() {
    notifyAppState(false, true);
    localStorage.removeItem("token");
    window.location.href = "index.html";
}
