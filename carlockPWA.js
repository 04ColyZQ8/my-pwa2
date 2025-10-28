// Send command to backend
async function sendCmd(action) {
    try {
        const endpoint = "https://carlock-backend-od8a.onrender.com/api/" + action;
        const res = await fetch(endpoint, { method: "POST" });
        const data = await res.json();
        console.log("Command sent:", action, data);
    } catch (err) {
        console.error("Failed to send command:", err);
    }
}

// Warm up backend & Blynk on page load
async function warmUpBackend() {
    try {
        const res = await fetch("https://carlock-backend-od8a.onrender.com/api/status");
        const data = await res.json();
        console.log("Backend & Blynk warmed up", data);
    } catch (err) {
        console.error("Warmup failed:", err);
    }
}

// Ping backend periodically to keep it awake (optional)
function keepBackendAlive(intervalMinutes = 4) {
    setInterval(async () => {
        try {
            await fetch("https://carlock-backend-od8a.onrender.com/api/status");
            console.log("Pinged backend to keep awake");
        } catch (err) {
            console.error("Ping failed:", err);
        }
    }, intervalMinutes * 60 * 1000); // default every 4 minutes
}

// Run warmup and keep-alive
window.addEventListener('load', () => {
    warmUpBackend();
    keepBackendAlive();
});
