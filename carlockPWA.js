function safeNumber(val) {
    if (Array.isArray(val)) val = val[0];
    const num = Number(val);
    return Number.isFinite(num) ? Math.round(num) : 0;
}

function updateEngineStatus(running, rpm, message) {
    const rpmEl = document.getElementById("engineRpmText");
    const runningEl = document.getElementById("engineRunningText");
    const msgEl = document.getElementById("engineMessageText");

    const safeRunning = safeNumber(running);
    const safeRpm = safeNumber(rpm);

    if (rpmEl) rpmEl.innerText = String(safeRpm);
    if (msgEl) msgEl.innerText = message || "Ready";

    if (runningEl) {
        runningEl.innerText = safeRunning ? "RUNNING" : "OFF";
        runningEl.classList.remove("on", "off");
        runningEl.classList.add(safeRunning ? "on" : "off");
    }
}
