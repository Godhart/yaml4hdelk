class RemoteFiles {

    serverTalk = null

    constructor(serverTalk) {
        this.serverTalk = serverTalk;
    }

    async remoteDomainsList() {
        // Returns available remote domains list
        return new Promise((resolve, reject) => {
            const remoteDomains = JSON.parse(await this.serverTalk.get(
                "rest/1.0/domains/domainsList"
            ).catch(function (e) {
                console.error('RemoteFiles.remoteFilesList() exception:', e);
                reject(e)
            })
            ).domains;
            resolve(remoteDomains)
        });
    }

    async remoteFilesList(dataDomain) {
        // Returns remote files list for specified domain as an Array
        return new Promise((resolve, reject) => {
            const remoteFiles = JSON.parse(await this.serverTalk.get(
                "rest/1.0/domain/" + dataDomain + "/filesList"
            ).catch(function (e) {
                console.error('RemoteFiles.remoteFilesList() exception:', e);
                reject(e)
            })
            ).files;
            resolve(remoteFiles)
        });
    }

    async remoteFilesHash(dataDomain, filesList) {
        // Returns hash for specified remote files as a Dictionary
        return new Promise((resolve, reject) => {
            const remoteHashes = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/filesHash",
                { "filesList": filesList }
            ).catch(function (e) {
                console.error('RemoteFiles.remoteFilesHash() exception:', e);
                reject(e)
            })
            ).hashes;
            resolve(remoteHashes)
        });
    }

    async remoteFilesLock(dataDomain, filesList) {
        // Returns lock id for specified remote files a Dictionary
        return new Promise((resolve, reject) => {
            const remoteLocks = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/filesLock",
                { "filesList": filesList }
            ).catch(function (e) {
                console.error('RemoteFiles.remoteFilesLock() exception:', e);
                reject(e)
            })
            ).locks;
            resolve(remoteLocks)
        });
    }

    // TODO: domain/<domain>/info/<file_path> to obtain per file info

    async remoteLock(dataDomain, filePath) {
        // Returns lock id for specified remote files a Dictionary
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/lock/" + filePath,
                { "set": True }
            ).catch(function (e) {
                console.error('RemoteFiles.remoteLock() exception:', e);
                reject(e)
            })
            );
            if (response.ok) {
                resolve(response.lock);
            } else {
                console.error("RemoteFiles.remoteLock() failed due to reason:" + response.reason)
                reject(null);
            }
        });
    }

    async remoteUnlock(dataDomain, filePath, lock) {
        // Returns lock id for specified remote files a Dictionary
        return new Promise((resolve, reject) => {
            const response = JSON.parse(await this.serverTalk.postJson(
                "rest/1.0/domain/" + dataDomain + "/unlock/" + filePath,
                { "lock": lock }
            ).catch(function (e) {
                console.error('RemoteFiles.remoteUnlock() exception:', e);
                reject(e)
            })
            );
            if (response.ok) {
                resolve(response.lock);
            } else {
                console.error("RemoteFiles.remoteUnlock() failed due to reason:" + response.reason)
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
        */
        return new Promise((resolve, reject) => {
            const fileData = JSON.parse(await this.serverTalk.post(
                "rest/1.0/domain/" + dataDomain + "/files/" + filePath,
                { "fields": ["content", "hash", "lock"] }
            ).catch(function (e) {
                console.error('RemoteFiles.getFile() exception:', e);
                reject(e)
            })
            );
            resolve(fileData);
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
                { "content": fileData.content, "hash": fileData.hash, "lock": fileData.lock }
            ).catch(function (e) {
                console.error('RemoteFiles.saveFile() exception:', e);
                reject(e)
            })
            );
            if (response.ok) {
                fileData.source = response.content;
                fileData.hash = response.hash;
                resolve(fileData)
            } else {
                console.error("RemoteFiles.saveFile() failed due to reason:" + response.reason)
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
            if (response.ok) {
                resolve(response.dia)
            } else {
                console.error("RemoteFiles.diagramData() failed due to reason:" + response.reason)
                reject(null);
            }
        });
    }
}
