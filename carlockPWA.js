async function sendCmd(action) {
    let endpoint = "https://carlock-backend-od8a.onrender.com/api/" + action;
    let res = await fetch(endpoint, { method: "POST" });
    let data = await res.json();
    console.log(data);
    //alert("Command sent: " + action);
}
