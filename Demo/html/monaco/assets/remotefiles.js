class RemoteFiles {

    serverTalk = null
    secret = null

    constructor(serverTalk) {
        this.serverTalk = serverTalk;
        let secret = localStorage.getItem("yaml4schm-monaco-secret")
        if (secret === undefined) {
            secret = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
            localStorage.setItem("yaml4schm-monaco-secret", secret)
        }
        this.secret = secret
    }

    async remoteDomainsList() {
        // Returns available remote domains list
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.get(
                "rest/1.0/domains/domainsList"
            ).catch(function (e) {
                console.error('RemoteFiles.remoteFilesList() exception:', e);
                reject(e)
            })
            );
            if (!response.SUCCESS) {
                console.error("RemoteFiles.remoteDomainsList() failed due to reason:" + response.ERROR)
                reject(response.ERROR)
            }
            resolve(response.domains)
        });
    }

    async remoteFilesList(dataDomain) {
        // Returns remote files list for specified domain as an Array
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.get(
                "rest/1.0/domain/" + dataDomain + "/filesList"
            ).catch(function (e) {
                console.error('RemoteFiles.remoteFilesList() exception:', e);
                reject(e)
            })
            );
            if (!response.SUCCESS) {
                console.error("RemoteFiles.remoteFilesList() failed due to reason:" + response.ERROR)
                reject(response.ERROR)
            }
            resolve(response.files)
        });
    }

    async remoteFilesHash(dataDomain, filesList) {
        // Returns hash for specified remote files as a Dictionary
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/filesHash",
                { "filesList": filesList }
            ).catch(function (e) {
                console.error('RemoteFiles.remoteFilesHash() exception:', e);
                reject(e)
            })
            );
            if (!response.SUCCESS) {
                console.error("RemoteFiles.remoteFilesHash() failed due to reason:" + response.ERROR)
                reject(response.ERROR)
            }
            resolve(response.hashes)
        });
    }

    async remoteFilesLock(dataDomain, filesList) {
        // Returns lock id for specified remote files a Dictionary
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/filesLock",
                { "filesList": filesList }
            ).catch(function (e) {
                console.error('RemoteFiles.remoteFilesLock() exception:', e);
                reject(e)
            })
            )
            if (!response.SUCCESS) {
                console.error("RemoteFiles.remoteFilesLock() failed due to reason:" + response.ERROR)
                reject(response.ERROR)
            }
            resolve(response.locks);
        });
    }

    async remoteLock(dataDomain, filePath, force, test) {
        // Returns lock id for specified remote files a Dictionary
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/lock/" + filePath,
                { "set": True, "secret": this.secret, "force": force, "test": test}
            ).catch(function (e) {
                console.error('RemoteFiles.remoteLock() exception:', e);
                reject(e)
            })
            );
            if (response.SUCCESS) {
                resolve(response.lock);
            } else {
                console.error("RemoteFiles.remoteLock() failed due to reason:" + response.ERROR)
                reject(null);
            }
        });
    }

    async remoteUnlock(dataDomain, filePath) {
        // Returns lock id for specified remote files a Dictionary
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/unlock/" + filePath,
                { "secret": this.secret }
            ).catch(function (e) {
                console.error('RemoteFiles.remoteUnlock() exception:', e);
                reject(e)
            })
            );
            if (response.SUCCESS) {
                resolve(response.lock);
            } else {
                console.error("RemoteFiles.remoteUnlock() failed due to reason:" + response.ERROR)
                reject(null);
            }
        });
    }

    async getFile(dataDomain, filePath) {
        /*
        Returns remote file content and meta for specified domain / file path as an dictionary
        fileData Contains:
            content:    content of the file
            hash:       server's hash for the file content that would be checked later on save
            lock:       server's lock for the file
            timestamp:  last modification timestamp
        */
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.post(
                "rest/1.0/domain/" + dataDomain + "/files/" + filePath,
                { "fields": ["content", "hash", "lock", "timestamp"] }
            ).catch(function (e) {
                console.error('RemoteFiles.getFile() exception:', e);
                reject(e)
            })
            );
            if (!response.SUCCESS) {
                console.error("RemoteFiles.getFile() failed due to reason:" + response.ERROR)
                reject(response.ERROR)
            }
            resolve(response.data);
        });
    }

    async saveFile(dataDomain, filePath, fileData) {
        /*
        Saves content of specified file
        In case of success updates fileData with new hash and content,
        received from server
        */
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/save/" + filePath,
                {
                    "content": fileData.content, "hash": fileData.hash, "secret": this.secret,
                    "fields": ["content", "hash", "timestamp"]
                }
            ).catch(function (e) {
                console.error('RemoteFiles.saveFile() exception:', e);
                reject(e)
            })
            );
            if (response.SUCCESS) {
                fileData.source = response.data.content;
                fileData.hash = response.data.hash;
                fileData.timestamp = response.data.timestamp;
                resolve(fileData)
            } else {
                console.error("RemoteFiles.saveFile() failed due to reason:" + response.ERROR)
                reject(null);
            }
        });
    }

    async diagramData(dataDomain, filePath, alteredContent, tool) {
        // Loads diagram for specified file
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/dia/" + filePath,
                { "tool": tool, "alteredContent": alteredContent }
            ).catch(function (e) {
                console.error('RemoteFiles.remoteFilesHash() exception:', e);
                reject(e)
            })
            );
            if (response.SUCCESS) {
                resolve(response.dia)
            } else {
                console.error("RemoteFiles.diagramData() failed due to reason:" + response.ERROR)
                reject(null);
            }
        });
    }
}
