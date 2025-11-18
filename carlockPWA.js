const API_BASE = "https://carlock-backend-od8a.onrender.com";

window.addEventListener('load', async () => {
    const token = localStorage.getItem("token");
    if (!token) window.location.href = "index.html";

    loadMapFromStorage();
});

// Send commands
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

// NEW: Get location
async function getLocation() {
    const token = localStorage.getItem("token");
    if (!token) return;

    const res = await fetch(`${API_BASE}/api/getCarLocation`, {
        headers: { "Authorization": "Bearer " + token }
    });

    const data = await res.json();

    if (data.lat) {
        const mapUrl = data.mapUrl;
        localStorage.setItem("lastMapUrl", mapUrl);
        document.getElementById("mapThumb").src =
            `https://maps.googleapis.com/maps/api/staticmap?center=${data.lat},${data.lng}&zoom=18&size=400x400&key=${data.api}`;
        loadMapFromStorage();
    }
}

// Load last map
function loadMapFromStorage() {
    const url = localStorage.getItem("lastMapUrl");
    if (!url) return;

    document.getElementById("mapThumb").src =
        url.replace("https://www.google.com/maps?q=", 
                    "https://maps.googleapis.com/maps/api/staticmap?center=")
           + `&zoom=18&size=400x400`;
}

// Clicking thumbnail → open full screen
document.getElementById("mapThumb").onclick = () => {
    const url = localStorage.getItem("lastMapUrl");
    if (url) window.open(url, "_blank");
};

function logout() {
    localStorage.removeItem("token");
    window.location.href = "index.html";
}
