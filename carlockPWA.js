const API_BASE = "https://carlock-backend-od8a.onrender.com"; // your Render backend URL

// Login function
async function login() {
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  try {
    const res = await fetch(`${API_BASE}/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (data.token) {
      localStorage.setItem("token", data.token);
      // Go to main control page
      window.location.href = "carlockPWA.html";
    } else {
      alert(data.message || "Invalid credentials");
    }
  } catch (err) {
    console.error("Login failed:", err);
    alert("Login failed. Check backend URL.");
  }
}

// Send command function
async function sendCmd(action) {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("Not logged in!");
    window.location.href = "index.html";
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/${action}`, {
      method: "POST",
      headers: { "Authorization": "Bearer " + token }
    });

    const data = await res.json();
    console.log(action, data);
    alert(`${action} command sent!`);
  } catch (err) {
    console.error(action, "failed:", err);
  }
}
