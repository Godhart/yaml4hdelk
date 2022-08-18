class RemoteData {
    remoteFiles = null
    dataDomain = null
    domains = null      // list with all available domains
    files = null        // list with file paths
    hashes = null       // dict, key is file path
    locks = null        // dict, key is file path

    constructor(remoteFiles, dataDomain) {
        this.remoteFiles = remoteFiles;
        this.dataDomain = dataDomain;
        this.update();
    }

    update() {
        this.remoteFiles.remoteDomainsList()
            .then(
                (domainsList) => { this.domains = domainsList },
                () => { this.domains = null }
            )

        this.remoteFiles.remoteFilesList(this.dataDomain)
            .then(
                (filesList) => { this.files = filesList },
                () => { this.files = null }
            )

        this.remoteFiles.remoteFilesHash(this.dataDomain, this.filesList)
            .then(
                (hashes) => { this.hashes = hashes },
                () => { this.hashes = null }
            )

        this.remoteFiles.remoteFilesLock(this.dataDomain, this.filesList)
            .then(
                (locks) => { this.remoteFilesLock },
                () => { this.locks = null }
            )
    }
}
