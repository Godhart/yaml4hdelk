class ServerTalk{
    serverUrl = null;

    constructor (serverUrl) {
        this.serverUrl = serverUrl;
    }

    postJson(url, json, callback) {
        const xhttp=new XMLHttpRequest();
        xhttp.onload = function() {callback(this);}
        xhttp.open("POST", this.serverUrl + "/" + url);
        xhttp.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
        xhttp.send(json);
    }
}
