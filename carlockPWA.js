const API_BASE = "https://carlock-backend-od8a.onrender.com";

// Default placeholder image
const DEFAULT_MAP =
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/World_map_placeholder.png/640px-World_map_placeholder.png";

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

// Get car location
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

            // fallback to placeholder
            document.getElementById("mapThumb").src = DEFAULT_MAP;
        }
    } catch (err) {
        console.error("Failed to fetch car location:", err);

        // fallback to placeholder
        document.getElementById("mapThumb").src = DEFAULT_MAP;
    }
}

// Load last map
function loadMapFromStorage() {
    const url = localStorage.getItem("lastMapUrl");

    if (!url) {
        document.getElementById("mapThumb").src = DEFAULT_MAP;
        return;
    }

    document.getElementById("mapThumb").src = url;
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
