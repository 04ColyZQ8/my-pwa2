const API_BASE = "https://carlock-backend-od8a.onrender.com"; // backend URL

// -------------------------
// Warmup backend on page load
// -------------------------
window.addEventListener('load', async () => {
    const token = localStorage.getItem("token");

    // If no token, only redirect if not on login page
    if (!token) {
        if (!window.location.href.endsWith("index.html")) {
            window.location.href = "index.html";
        }
        return;
    }

    // Try warming up the backend
    try {
        const res = await fetch(`${API_BASE}/api/warmup`, {
            headers: { "Authorization": "Bearer " + token }
        });
        if (!res.ok) throw new Error("Warmup failed with status " + res.status);
        console.log("Backend warmed up!");
    } catch (err) {
        console.error("Warmup failed:", err);
    }
});

// -------------------------
// Send commands to backend
// -------------------------
async function sendCmd(action) {
    const token = localStorage.getItem("token");
    if (!token) {
        if (!window.location.href.endsWith("index.html")) {
            window.location.href = "index.html";
        }
        return;
    }

    // Map frontend actions to backend endpoints
    const actionMap = {
        soundAlarm: "sound",
        stopAlarm: "stopSound",
        flashLights: "flash",
        stopLights: "stopFlash",
        remoteStart: "remoteStart"
    };
    const apiAction = actionMap[action] || action;

    try {
        const res = await fetch(`${API_BASE}/api/${apiAction}`, {
            method: "POST",
            headers: { "Authorization": "Bearer " + token }
        });

        if (!res.ok) {
            console.error(`${action} failed with status ${res.status}`);
            return;
        }

        const data = await res.json();
        console.log(`${action} command sent`, data);

    } catch (err) {
        console.error(`${action} command failed:`, err);
    }
}
