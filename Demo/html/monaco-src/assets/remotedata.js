class RemoteData {
    /* Represents current state of remote data */

    remoteFiles = null
    dataDomain = null
    domains = []        // list with all available domains
    files = []          // list with file paths
    filesMeta = {}      // dict, key is file path
    lock = null         // value for files locks when they are locked by me
    ifCreated = null

    constructor(remoteFiles, dataDomain) {
        this.ifCreated = new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                this.remoteFiles = remoteFiles;
                return this.switchDomain(dataDomain)
                    .then(_ => this.remoteFiles.remoteLock(this.dataDomain, "test", false, true))
                    .then(lock => this.lock = lock)
            })
    }

    switchDomain = function (dataDomain) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                this.dataDomain = dataDomain;
                return this.updateAll()
            })
    }

    updateAll = function () {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                this.domains = []
                this.files = []
                this.filesMeta = {}
                return this.remoteFiles.remoteDomainsList()
                    .then((domains) => { this.domains = domains })
                    .then(_ => this.remoteFiles.remoteFilesList(this.dataDomain))
                    .then((files) => { this.files = files })
                    .then(_ => this.quickUpdate(this.files))
            })
    }

    quickUpdate = function (files) {
        return this.remoteFiles.getFiles(this.dataDomain, files, ["hash", "lock", "timestamp"])
            .then((data) => {
                files.forEach(item => {
                    if (data[item] !== undefined) {
                        this.filesMeta[item] = data[item]
                    } else {
                        this.filesMeta[item] = { "hash": null, "lock": null, "timestamp": null }
                    }
                })
            })
    }

}
