const API_BASE = "https://carlock-backend-od8a.onrender.com";
const pending = {};

window.addEventListener('load', async () => {
    const token = localStorage.getItem("token");
    if (!token) return window.location.href = "index.html";

    try {
        await fetch(`${API_BASE}/api/warmup`, { headers: { "Authorization": "Bearer " + token }});
        console.log("Backend warmed up!");
    } catch (err) {
        console.error("Warmup failed:", err);
    }
});

// -------------------------
// Command buttons
// -------------------------
async function sendCmd(action) {
    const token = localStorage.getItem("token");
    if (!token) return window.location.href = "index.html";

    if (pending[action]) return;
    pending[action] = true;

    const btn = document.querySelector(`[onclick="sendCmd('${action}')"]`);
    if (btn) btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/api/${action}`, {
            method: "POST",
            headers: { "Authorization": "Bearer " + token }
        });
        const data = await res.json();
        console.log(`${action}:`, data);
    } catch (err) {
        console.error(`${action} failed:`, err);
    } finally {
        pending[action] = false;
        if (btn) btn.disabled = false;
    }
}

// -------------------------
// Get Vehicle Location
// -------------------------
async function getVehicleLocation() {
    const token = localStorage.getItem("token");
    if (!token) { alert("Please log in."); return; }

    try {
        const res = await fetch(`${API_BASE}/api/geoscan`, {
            method: "POST",
            headers: { "Authorization": "Bearer " + token }
        });
        const data = await res.json();
        console.log("Geo response:", data);

        if (data.location) {
            const lat = data.location.lat;
            const lng = data.location.lng;
            updateMap(lat, lng);
        } else {
            alert("Location not ready yet. Make sure ESP32 sent scan data.");
        }
    } catch (err) {
        console.error("getVehicleLocation failed:", err);
    }
}

function updateMap(lat, lng) {
    const url = `${API_BASE}/api/staticmap?lat=${lat}&lng=${lng}`;
    document.getElementById("mapImg").src = url;
    document.getElementById("mapFull").src = url;
}

function openFullMap() { document.getElementById("mapModal").style.display = "flex"; }
function closeFullMap() { document.getElementById("mapModal").style.display = "none"; }
function logout() { localStorage.removeItem("token"); window.location.href = "index.html"; }

