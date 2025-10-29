const API_BASE = "https://carlock-backend-od8a.onrender.com"; // backend URL

// -------------------------
// Warmup backend on page load
// -------------------------
window.addEventListener('load', async () => {
    const token = localStorage.getItem("token");
    if (token) {
        try {
            await fetch(`${API_BASE}/api/warmup`, {
                headers: { "Authorization": "Bearer " + token }
            });
            console.log("Backend warmed up!");
        } catch (err) {
            console.error("Warmup failed:", err);
        }
    } else {
        window.location.href = "index.html";
    }
});

// -------------------------
// Send commands to backend
// -------------------------
async function sendCmd(action) {
    const token = localStorage.getItem("token");
    if (!token) {
        //alert("Not logged in!");
        window.location.href = "index.html";
        return;
    }

    // Map frontend actions to backend endpoints
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
        //console.log(action, data);
        //alert(`${action} command sent!`);
    } catch (err) {
        //console.error(action, "failed:", err);
        //alert("Failed to send command. Check backend.");
    }
}
