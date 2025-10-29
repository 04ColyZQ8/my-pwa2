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
async function sendCmd(action) {
    const token = localStorage.getItem("token");
    if (!token) {
        if (!window.location.href.includes("index.html")) {
            window.location.href = "index.html";
        }
        return;
    }

    let apiAction = action;
    switch (action) {
        case 'soundAlarm': apiAction = 'sound'; break;
        case 'stopAlarm': apiAction = 'stopSound'; break;
        case 'flashLights': apiAction = 'flash'; break;
        case 'stopLights': apiAction = 'stopFlash'; break;
        case 'remoteStart': apiAction = 'remoteStart'; break;
    }

    try {
        const res = await fetch(`${API_BASE}/api/${apiAction}`, {
            method: "POST",
            headers: { "Authorization": "Bearer " + token }
        });
        const data = await res.json();
        console.log(`${action} command sent:`, data);
    } catch (err) {
        console.error(`${action} failed:`, err);
    }
}

// -------------------------
// Logout
// -------------------------
function logout() {
    localStorage.removeItem("token");
    window.location.href = "index.html";
}
