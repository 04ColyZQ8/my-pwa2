async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok) {
        localStorage.setItem('authToken', data.token);
        window.location.href = "/dashboard";
    } else {
        document.getElementById('msg').textContent = data.message;
    }
}

// Auto-login if already authenticated
window.addEventListener('load', () => {
    const token = localStorage.getItem('authToken');
    if (token) {
        window.location.href = "/dashboard";
    }
});
