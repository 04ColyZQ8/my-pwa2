async function sendCmd(action) {
    let endpoint = "/api/" + action;
    let res = await fetch(endpoint, { method: "POST" });
    let data = await res.json();
    console.log(data);
}
