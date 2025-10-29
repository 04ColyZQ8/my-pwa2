const API_BASE = "https://carlock-backend-od8a.onrender.com"; // Render backend URL

async function sendCmd(action) {
    const token = localStorage.getItem("token");
    if (!token) {
        alert("Not logged in!");
        window.location.href = "index.html";
        return;
    }

    // Map frontend action to backend endpoint
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
        console.log(action, data);
        alert(`${action} command sent!`);
    } catch (err) {
        console.error(action, "failed:", err);
        alert("Failed to send command. Check backend.");
    }
}
