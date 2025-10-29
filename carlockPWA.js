// -----------------------
// Login & Token
// -----------------------
async function login(username, password) {
    try {
        const res = await fetch('https://carlock-backend-od8a.onrender.com/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok) {
            localStorage.setItem('authToken', data.token);
            return true;
        } else {
            alert(data.message);
            return false;
        }
    } catch (err) {
        console.error("Login failed:", err);
        return false;
    }
}

// -----------------------
// Send commands
// -----------------------
async function sendCmd(action) {
    try {
        const token = localStorage.getItem('authToken');
        if (!token) {
            alert("Please login first!");
            return;
        }
        const endpoint = "https://carlock-backend-od8a.onrender.com/api/" + action;
        const res = await fetch(endpoint, { 
            method: "POST",
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await res.json();
        console.log("Command sent:", action, data);
    } catch (err) {
        console.error("Failed to send command:", err);
    }
}

// -----------------------
// Warmup backend
// -----------------------
async function warmUpBackend() {
    try {
        const token = localStorage.getItem('authToken');
        if (!token) return;
        const res = await fetch("https://carlock-backend-od8a.onrender.com/api/status", {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await res.json();
        console.log("Backend warmed up", data);
    } catch (err) {
        console.error("Warmup failed:", err);
    }
}

// -----------------------
// Keep backend alive
// -----------------------
function keepBackendAlive(intervalMinutes = 4) {
    setInterval(async () => {
        try {
            const token = localStorage.getItem('authToken');
            if (!token) return;
            await fetch("https://carlock-backend-od8a.onrender.com/api/status", {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            console.log("Pinged backend to keep awake");
        } catch (err) {
            console.error("Ping failed:", err);
        }
    }, intervalMinutes * 60 * 1000);
}

// -----------------------
// Run warmup on load
// -----------------------
window.addEventListener('load', () => {
    warmUpBackend();
    keepBackendAlive();
});
