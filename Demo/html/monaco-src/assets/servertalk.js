class ServerTalk {
    serverUrl = null;

    constructor(serverUrl) {
        this.serverUrl = serverUrl;
    }

    fullUrl(url) {
        return this.serverUrl + "/" + url
    }

    postJson(url, json) {
        return new Promise(function (resolve, reject) {
            const xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function (e) {
                if (xhttp.readyState === 4) {
                    if (xhttp.status === 200) {
                        resolve(xhttp.response)
                    } else {
                        reject(xhttp.status)
                    }
                }
            }
            xhttp.ontimeout = function () {
                reject('timeout')
            }
            xhttp.open("POST", this.fullUrl(url), true);
            xhttp.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
            xhttp.send(JSON.stringify(json));
        })
    }

    get(url) {
        return new Promise(function (resolve, reject) {
            const xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function (e) {
                if (xhttp.readyState === 4) {
                    if (xhttp.status === 200) {
                        resolve(xhttp.response)
                    } else {
                        reject(xhttp.status)
                    }
                }
            }
            xhttp.ontimeout = function () {
                reject('timeout')
            }
            xhttp.open("GET", this.fullUrl(url), true);
            xhttp.send();
        })
    }
}
