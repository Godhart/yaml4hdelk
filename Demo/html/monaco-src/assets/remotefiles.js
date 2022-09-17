class RemoteFiles {
    /* Interacts with server to get and save data */

    serverTalk = null
    secret = null

    constructor(serverTalk) {
        this.serverTalk = serverTalk
        let secret = localStorage.getItem("yaml4schm-monaco-secret")
        if (secret === null) {
            secret = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
            localStorage.setItem("yaml4schm-monaco-secret", secret)
        }
        this.secret = secret
    }

    remoteDomainsList = async function () {
        // Returns available remote domains list
        const response = JSON.parse(await this.serverTalk.get("rest/1.0/domains/domainsList"))
        if (!response.SUCCESS) {
            console.error("RemoteFiles.remoteDomainsList() failed due to reason:" + response.ERROR)
            throw Error(response.ERROR)
        }
        return response.domains
    }

    remoteFilesList = async function (dataDomain) {
        // Returns remote files list for specified domain as an Array
        const response = JSON.parse(await this.serverTalk.get(
            "rest/1.0/domain/" + dataDomain + "/filesList"
        ))
        if (!response.SUCCESS) {
            console.error("RemoteFiles.remoteFilesList() failed due to reason:" + response.ERROR)
            throw Error(response.ERROR)
        }
        return response.files
    }

    remoteLock = async function (dataDomain, filePath, force, test) {
        // Returns lock id for specified remote files a Dictionary
        const response = JSON.parse(await this.serverTalk.postJson(
            "rest/1.0/domain/" + dataDomain + "/lock/" + filePath,
            { "set": true, "secret": this.secret, "force": force, "test": test }
        ))
        if (response.SUCCESS) {
            return response.lock
        } else {
            console.error("RemoteFiles.remoteLock() failed due to reason:" + response.ERROR)
            throw Error(response.ERROR)
        }
    }

    remoteUnlock = async function (dataDomain, filePath) {
        // Returns lock id for specified remote files a Dictionary
        const response = JSON.parse(await this.serverTalk.postJson(
            "rest/1.0/domain/" + dataDomain + "/unlock/" + filePath,
            { "secret": this.secret }
        ))
        if (response.SUCCESS) {
            return response.lock
        } else {
            console.error("RemoteFiles.remoteUnlock() failed due to reason:" + response.ERROR)
            throw Error(response.ERROR)
        }
    }

    getFiles = async function (dataDomain, filesList, fields) {
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
        const response = JSON.parse(await this.serverTalk.postJson(
            "rest/1.0/domain/" + dataDomain + "/get",
            {
                "filesList": filesList,
                "fields": fields
            }
        ))
        if (!response.SUCCESS) {
            console.error("RemoteFiles.getFiles() failed due to reason:" + response.ERROR)
            throw Error(response.ERROR)
        }
        return response.data
    }

    saveFiles = async function (dataDomain, filesData) {
        /*
        Saves content of specified files
        fileData should be a dict with file path as key and dict with following fields as value:
        - content
        - hash from previous read file operation
        - secret to unlock locked file
        */
        const response = JSON.parse(await this.serverTalk.postJson(
            "rest/1.0/domain/" + dataDomain + "/save/",
            {
                "data": filesData,
                "fields": ["content", "hash", "timestamp"]
            }
        ))
        if (response.SUCCESS) {
            return response.data
        } else {
            console.error("RemoteFiles.saveFiles() failed due to reason:" + response.ERROR)
            throw Error(null)
        }
    }

    diagramData = async function (dataDomain, filePath, alteredContent, tool) {
        // Loads diagram for specified file
        const response = JSON.parse(await this.serverTalk.postJson(
            "rest/1.0/domain/" + dataDomain + "/dia/" + filePath,
            { "tool": tool, "alteredContent": alteredContent }
        ))
        if (response.SUCCESS) {
            return response.dia
        } else {
            console.error("RemoteFiles.diagramData() failed due to reason:" + response.ERROR)
            throw Error(response.ERROR)
        }
    }
}
