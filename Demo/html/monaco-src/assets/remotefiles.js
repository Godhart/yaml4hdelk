class RemoteFiles {
    /* Interacts with server to get and save data */

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

    async getFiles(dataDomain, filesList, fields) {
        /*
        Returns remote files content and meta for specified domain as an dictionary
        filesList is expected to be a list with files paths
        Returned data is a dict with file path as key and dict with specified fields as value.
        If fields are note specified then following fields would be in result:
            content:    content of the file
            hash:       server's hash for the file content that would be checked later on save
            lock:       server's lock for the file
            timestamp:  last modification timestamp
        */
        if (fields === undefined) {
            fields = ["content", "hash", "lock", "timestamp"]
        }
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.post(
                "rest/1.0/domain/" + dataDomain + "/get",
                {
                    "filesList": filesList,
                    "fields": ["content", "hash", "lock", "timestamp"]
                }
            ).catch(function (e) {
                console.error('RemoteFiles.getFiles() exception:', e);
                reject(e)
            })
            );
            if (!response.SUCCESS) {
                console.error("RemoteFiles.getFiles() failed due to reason:" + response.ERROR)
                reject(response.ERROR)
            }
            resolve(response.data);
        });
    }

    async saveFiles(dataDomain, filesData) {
        /*
        Saves content of specified files
        fileData should be a dict with file path as key and dict with following fields as value:
        - content
        - hash from previous read file operation
        - secret to unlock locked file
        */
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/save/",
                {
                    "data": filesData,
                    "fields": ["content", "hash", "timestamp"]
                }
            ).catch(function (e) {
                console.error('RemoteFiles.saveFiles() exception:', e);
                reject(e)
            })
            );
            if (response.SUCCESS) {
                resolve(response.data)
            } else {
                console.error("RemoteFiles.saveFiles() failed due to reason:" + response.ERROR)
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
