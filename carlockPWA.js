const API_BASE = "https://carlock-backend-od8a.onrender.com";

// -------------------------
// Warmup backend on page load
// -------------------------
window.addEventListener('load', async () => {
    const token = localStorage.getItem("token");
    if (!token && !window.location.href.includes("index.html")) {
        window.location.href = "index.html";
        return;
    }

    if (token) {
        try {
            await fetch(`${API_BASE}/api/warmup`, {
                headers: { "Authorization": "Bearer " + token }
            });
            console.log("Backend warmed up!");
        } catch (err) {
            console.error("Warmup failed:", err);
        }
    }
});

// -------------------------
// Send commands to backend
// -------------------------
const pending = {}; // track pending requests to avoid double-clicks

async function sendCmd(action) {
    const token = localStorage.getItem("token");
    if (!token) {
        if (!window.location.href.includes("index.html")) {
            window.location.href = "index.html";
        }
        return;
    }

    if (pending[action]) return; // skip if request is in progress
    pending[action] = true;

    const button = document.querySelector(`[onclick="sendCmd('${action}')"]`);
    if (button) button.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/api/${action}`, {
            method: "POST",
            headers: { "Authorization": "Bearer " + token }
        });
        const data = await res.json();
        console.log(`${action} sent:`, data);
    } catch (err) {
        console.error(`${action} failed:`, err);
    } finally {
        pending[action] = false;
        if (button) button.disabled = false;
    }
}

// -------------------------
// Optional: logout
// -------------------------
function logout() {
    localStorage.removeItem("token");
    window.location.href = "index.html";
}
