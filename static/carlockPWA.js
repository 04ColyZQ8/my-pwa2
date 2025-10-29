async function sendCmd(action) {
    try {
        const token = localStorage.getItem('authToken');
        const res = await fetch('/api/' + action, {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await res.json();
        console.log("Command:", action, data);
    } catch (err) {
        console.error("Error sending command:", err);
    }
}

function logout() {
    localStorage.removeItem('authToken');
    window.location.href = "/";
}
