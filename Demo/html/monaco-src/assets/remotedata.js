class RemoteData {
    /* Represents current state of remote data */

    remoteFiles = null
    dataDomain = null
    domains = []        // list with all available domains
    files = []          // list with file paths
    filesMeta = {}      // dict, key is file path
    lock = null         // value for files locks when they are locked by me

    constructor(remoteFiles, dataDomain) {
        this.remoteFiles = remoteFiles;
        this.switchDomain(dataDomain);
        this.remoteFiles.remoteLock(this.dataDomain, "test", False, True)
            .then(
                (lock) => this.lock = lock
            )
    }

    switchDomain(dataDomain) {
        this.dataDomain = dataDomain;
        this.updateAll()
    }

    updateAll() {
        this.domains = []
        this.files = []
        this.filesMeta = {}
        this.remoteFiles.remoteDomainsList()
            .then(
                (domains) => { this.domains = domains }
            )
            .then(
                () => { return this.remoteFiles.remoteFilesList(this.dataDomain) }
            )
            .then(
                (files) => { this.files = files; this.quickUpdate(this.files) }
            )
    }

    quickUpdate(files) {
        this.remoteFiles.getFiles(this.dataDomain, files, ["hash", "lock", "timestamp"])
        .then(
            (data) => {
                files.forEach(item => {
                    if (data[item] !== undefined) {
                        this.filesMeta[item] = data[item]
                    } else {
                        this.filesMeta[item] = {"hash": null, "lock": null, "timestamp": null}
                    }
                });
            }
        )
    }

}
