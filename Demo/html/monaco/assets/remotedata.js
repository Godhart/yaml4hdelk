class RemoteData {
    remoteFiles = null
    dataDomain = null
    domains = []        // list with all available domains
    files = []          // list with file paths
    hashes = {}         // dict, key is file path
    locks = {}          // dict, key is file path
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
        this.hashes = {}
        this.locks = {}
        this.remoteFiles.remoteDomainsList()
            .then(
                (domains) => { this.domains = domains }
            )
            .then(
                () => { return this.remoteFiles.remoteFilesList(this.dataDomain) }
            )
            .then(
                (files) => { this.files = files }
            )
            .then(
                () => { return this.remoteFiles.remoteFilesHash(this.dataDomain, this.files) }
            )
            .then(
                (hashes) => { this.hashes = hashes }
            )
            .then(
                () => { return this.remoteFiles.remoteFilesLock(this.dataDomain, this.files) }
            )
            .then(
                (locks) => { this.locks = locks }
            )
    }

    quickUpdate(files) {
        this.remoteFiles.remoteFilesHash(this.dataDomain, files)
            .then(
                (hashes) => {
                    for (const [key, value] of Object.entries(hashes)) {
                        this.hashes[key] = value;
                    }
                }
            )
        this.remoteFiles.remoteFilesLock(this.dataDomain, files)
            .then(
                (locks) => {
                    for (const [key, value] of Object.entries(locks)) {
                        this.locks[key] = value;
                    }
                }
            )
    }

}
