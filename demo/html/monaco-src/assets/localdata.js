class FileData {
    /* Class to store misc file related data */
    currentValue = undefined    // Current value. if undefined then value weren't loaded/set yet for optimization purposes
    problemsEditor = 0          // Amount of problems detected by editor
    problemsRemote = 0          // Amount of problems detected by server
    checkoutValue = undefined   // Initial value, that were received from server on checkout. if undefined then value weren't loaded/set yet for optimization purposes
    checkoutTimestamp = 0       // Initial value timestamp, that were received from server on checkout
    checkoutHash = null         // Hash that were received from server on checkout
    currentTimestamp = 0        // Last modification timestamp
    isFav = false               // Favorite mark
    pendingRemove = false       // If file is going to be removed
}


getCurrentDomain = function () {
    return new Promise((resolve, reject) => {
        let domain = localStorage.getItem("yaml4schm-monaco-domain")
        if (domain !== null) {
            resolve(domain)
        } else {
            reject("Currently no domain")
        }
    })
}

setCurrentDomain = function (value) {
    return new Promise((resolve, reject) => {
        localStorage.setItem("yaml4schm-monaco-domain", value)
        resolve(true)
    })
}

const SESSION = "session"
const FILES_DATA = "filesData"
const CURRENT_TAB = "currentTab"
const ACTIVE_TABS = "activeTabs"

class LocalData {
    /* Local data storage */

    session = null      // Current session timestamp. Used to understand if session is outdated
    // (detect if another session were opened on other browser tab)
    filesData = {}      // Dict with file data. Key is file path, value is FileData instance
    activeTabs = []     // List of active tabs, that should be displayed in editor. Value is file path
    currentTab = ""     // Currently selected tab. Value is file path
    dataDomain = ""     // Current data domain
    co = {}
    ifCreated = null
    remoteData = null
    remoteFiles = null

    constructor(domain) {
        this.ifCreated = this.switchDomain(domain)
    }

    switchDomain = function (dataDomain) {
        // Switches current active domain to work with
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                if (this.dataDomain !== "" && this.dataDomain !== undefined && this.dataDomain !== null) {
                    return this.storeAll();
                }
            })
            .then(() => {
                if (this.session !== null) {
                    return this.releaseSession();
                }
            })
            .then(() => {
                this.dataDomain = dataDomain;
                this.co = {}
                this.co[SESSION] = "yaml4schm-monaco-" + dataDomain + "-session"
                this.co[FILES_DATA] = "yaml4schm-monaco-" + dataDomain + "-filesData"
                this.co[CURRENT_TAB] = "yaml4schm-monaco-" + dataDomain + "-currentTab"
                this.co[ACTIVE_TABS] = "yaml4schm-monaco-" + dataDomain + "-activeTabs"
            })
            .then(_ => this.newSession())
            .then(_ => this.reload())
    }

    _check_session = function (force) {
        return new Promise((resolve, reject) => {
            if (force === true) {
                resolve(true)
            }
            let session = null
            try {
                session = JSON.parse(localStorage.getItem(this.co.session))
            } catch (e) {
                reject("Failed to read session from local storage due to exception " + e)
            }
            if (session === this.session) {
                resolve(session)
            } else {
                reject("Session changed ( " + this.session + " => " + session + " )")
            }
        })
    }

    _store = function (key, value, force) {
        return this._check_session(force)
            .then(
                () => { localStorage.setItem(this.co[key], JSON.stringify(value)); }
            )
    }

    _restore = function (key, fallback, force) {
        return this._check_session(force)
            .then(() => {
                let value = localStorage.getItem(this.co[key]);
                try {
                    if (fallback !== undefined && value === null) {
                        return fallback
                    } else {
                        value = JSON.parse(value)
                        return value
                    }
                } catch (e) {
                    throw Error("Failed to parse value due to exception: " + e)
                }
            },
                (err) => { console.log("Error when restoring data '" + key + "': " + err); throw err })
    }

    newSession = function () {
        this.session = new Date().getTime()
        return this._store(SESSION, this.session, true);
    }

    releaseSession = function () {
        return this._store(SESSION, null);
    }

    reload = function () {
        // TODO: remove obsolete files (that were deleted on server and not changed)
        // TODO: mark changed files that were deleted on server
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                this.filesData = {};
                this.activeTabs = [];
                this.currentTab = "";
            })
            .then(_ => this._restore(FILES_DATA, {}))
            .then(
                (data) => {
                    for (const [key, value] of Object.entries(data)) {
                        this.filesData[key] = Object.assign(new FileData(), value);
                    }
                }
            )
            .then(_ => this._restore(ACTIVE_TABS, []))
            .then(
                (activeTabs) => {
                    activeTabs.forEach(tab => {
                        if (this.filesData[tab] !== undefined) {
                            this.activeTabs.push(tab);
                        }
                    })
                },
                (err) => { this.filesData = {}; throw err }
            )
            .then(_ => this._restore(CURRENT_TAB, ""))
            .then(
                (currentTab) => { this.currentTab = currentTab },
                (err) => { this.filesData = {}; this.activeTabs = []; throw err; }
            )
            .then(() => {
                if (!this.activeTabs.includes(this.currentTab)) {
                    if (this.activeTabs.length > 0) {
                        this.currentTab = this.activeTabs[0];
                    } else {
                        this.currentTab = "";
                    }
                }
            })
    }

    storeAll = function () {
        return this._store(FILES_DATA, this.filesData)
            .then(_ => this._store(ACTIVE_TABS, this.activeTabs))
            .then(_ => this._store(CURRENT_TAB, this.currentTab))
    }

    checkoutFileData = function (filePath, source, hash, timestamp) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                if (this.filesData[filePath] === undefined) {
                    this.filesData[filePath] = Object.assign(new FileData(), {
                        "currentValue": source,
                        "checkoutValue": source,
                        "checkoutTimestamp": timestamp,
                        "checkoutHash": hash,
                        "currentTimestamp": timestamp,
                    });
                    return this._store(FILES_DATA, this.filesData)
                } else {
                    console.error("LocalData.checkoutFileData(): File " + filePath + " is already in database");
                    throw Error("File " + filePath + " is already in database");
                }
            })
    }

    addTab = function (filePath) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                if (this.filesData[filePath] !== undefined) {
                    if (this.activeTabs.includes(filePath)) {
                        console.error("LocalData.addTab(): Tab is already in list");
                        throw Error("Tab is already in list");
                    }
                    this.activeTabs.push(filePath);
                } else {
                    console.error("LocalData.addTab(): No file " + filePath + " for tab in database");
                    throw Error("No file " + filePath + " for tab in database");
                }
            })
            .then(_ => this._store(ACTIVE_TABS, this.activeTabs))
    }

    updateFileData = function (filePath, source, hash, timestamp) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                if (this.filesData[filePath] !== undefined) {
                    let f = this.filesData[filePath];
                    if (source !== undefined && source !== null) {
                        f.checkoutValue = source
                    }
                    if (hash !== undefined && hash !== null) {
                        f.checkoutHash = hash
                    }
                    if (timestamp !== undefined && hash !== null) {
                        f.checkoutTimestamp = timestamp
                    }
                    return this._store(FILES_DATA, this.filesData)
                } else {
                    console.error("LocalData.updateFileData(): File " + filePath + "is not in database");
                    throw Error("File " + filePath + " is not in database");
                }
            })
    }

    updateFileValue = function (filePath, value) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                if (this.filesData[filePath] !== undefined) {
                    let f = this.filesData[filePath];
                    if (f.currentValue !== value) {
                        f.currentValue = value;
                        f.currentTimestamp = new Date().getTime();
                        return this._store(FILES_DATA, this.filesData)
                    }
                } else {
                    console.error("LocalData.updateFileValue(): File " + filePath + "is not in database");
                    throw Error("File " + filePath + " is not in database");
                }
            })
    }

    removeFile = function (filePath) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                if (this.filesData[filePath] !== undefined) {
                    return this.removeTab(filePath)
                        .then(() => {
                            delete this.filesData[filePath];
                            return this._store(FILES_DATA, this.filesData)
                        })
                        .then(
                            () => { return this.currentTab }
                        )
                } else {
                    console.error("LocalData.removeFile(): File " + filePath + "is not in database");
                    throw Error("File " + filePath + " is not in database");
                }
            })
    }

    removeTab = function (filePath) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                let tabs = [];
                let previousTab = "";
                let nextTab = "";
                this.activeTabs.forEach(tab => {
                    if (tab !== filePath) {
                        previousTab = tab;
                        tabs.push(tab);
                    } else {
                        nextTab = previousTab;
                    }
                })
                this.activeTabs = tabs;
                if (filePath == this.currentTab) {
                    this.currentTab = nextTab;
                }
            })
            .then(_ => this._store(ACTIVE_TABS, this.activeTabs))
            .then(_ => this._store(CURRENT_TAB, this.currentTab))
            .then(_ => { return this.currentTab })
    }

    switchTab = function (filePath) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                if (this.filesData[filePath] !== undefined) {
                    return this._store(CURRENT_TAB, filePath)
                        .then(
                            () => { this.currentTab = filePath },
                        )
                } else {
                    console.error("LocalData.currentTabSet(): File " + filePath + " is not in database");
                    throw Error("File " + filePath + " is not in database");
                }
            })
    }

    updateFilesAndTabs = function (data) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                this.activeTabs = []
                for (const [key, value] of Object.entries(data)) {
                    if (this.filesData[key] !== undefined) {
                        this.activeTabs.push(key);
                        if (this.filesData[key].currentValue != value) {
                            this.filesData[key].currentValue = value;
                            this.filesData[key].currentTimestamp = new Date().getTime();
                        }
                    }
                }
                if (!this.activeTabs.includes(this.currentTab)) {
                    if (this.activeTabs.length > 0) {
                        this.currentTab = this.activeTabs[0]
                    } else {
                        this.currentTab = "";
                    }
                }
            })
            .then(_ => this._store(FILES_DATA, this.filesData))
            .then(_ => this._store(ACTIVE_TABS, this.activeTabs))
    }

    updateProblemsEditor = function (data) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                const filePath = data.path;
                if (this.filesData[filePath] !== undefined) {
                    this.filesData[filePath].problemsEditor = data.problemsCount;
                    return this._store(FILES_DATA, this.filesData)
                }
                console.error("LocalData.updateProblemsEditor(): File " + data.path + " is not in database");
                throw Error("File " + data.path + " is not in database");
            })
    }

    updateProblemsRemote = function (data) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(() => {
                const filePath = data.filePath;
                if (this.filesData[filePath] !== undefined) {
                    this.filesData[filePath].problemsRemote = data.problemsCount;
                    return this._store(FILES_DATA, this.filesData)
                }
                console.error("LocalData.updateProblemsRemote(): File " + data.path + " is not in database");
                throw Error("File " + data.path + " is not in database");
            })
    }

    ensureFileData = function (filePath, wantContent) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(_ => {
                if (this.filesData[filePath] === undefined) {
                    return this.updateFromRemote(filePath)
                }
            })
            .then(_ => {
                if (wantContent === true) {
                    return this.updateContent(filePath)
                }
            })
    }

    updateFromRemote = function (filePath) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(_ => {
                if (this.remoteData === null) {
                    throw Error("No remote data attached!")
                }
                let fileMeta = this.remoteData.filesMeta[filePath]
                if (fileMeta === undefined) {
                    throw Error("File '" + filePath + "' is not found!")
                }
                return this.checkoutFileData(filePath, undefined, fileMeta.hash, fileMeta.timestamp)
            })
    }

    updateContent = function (filePath, force) {
        return new Promise((resolve, reject) => { resolve({ "needContent": false }) })
            .then(context => {
                let fileData = this.filesData[filePath]
                if (fileData === undefined) {
                    throw Error("File '" + filePath + "' is not found!")
                }
                if (this.remoteData === null) {
                    throw Error("No remote data attached!")
                }
                if (this.remoteFiles === null) {
                    throw Error("No remote files attached!")
                }
                if (force === true) {
                    context.needContent = true
                    return context
                }
                if (fileData.currentValue === undefined) {
                    // No content in local storage at all
                    context.needContent = true
                    return context
                }
                if (fileData.currentValue === fileData.checkoutValue
                    // Content is same as were on checkout but remote hash is different
                    && fileData.checkoutHash !== this.remoteData.filesMeta[filePath].hash) {
                    context.needContent = true
                    return context
                }
            })
            .then(context => {
                if (context.needContent) {
                    return this.remoteFiles.getFiles(this.dataDomain, [filePath], ["content", "hash", "timestamp"])
                        .then(remoteData => {
                            let fileData = this.filesData[filePath]
                            fileData.currentValue = remoteData.content
                            fileData.currentTimestamp = remoteData.timestamp
                            fileData.checkoutValue = remoteData.content
                            fileData.checkoutHash = remoteData.hash
                            fileData.checkoutTimestamp = remoteData.timestamp
                        })
                }
            })
    }

    currentValue = function (filePath) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(_ => this.ensureFileData(filePath, true))
            .then(_ => { return this.filesData[filePath].currentValue })
    }

    toggleFav = function (filePath, value) {
        return new Promise((resolve, reject) => { resolve(true) })
            .then(_ => this.ensureFileData(filePath))
            .then(_ => {
                if (value === undefined) {
                    value = !this.filesData[filePath].isFav
                }
                this.filesData[filePath].isFav = value
                return this.storeAll()
                    .then(_ => { return [filePath, value] })
            })
    }

    exportData = function (filePathPrefix, data) {
        if (filePathPrefix === undefined) {
            filePathPrefix = ""
        }
        for (const [filePath, value] of Object.entries(this.filesData)) {
            let key = filePathPrefix + filePath
            if (data[key] === undefined) {
                data[key] = { "added": true, "timestamp": value.timestamp }
                if (value.pendingRemove) {
                    data[key].removed = true
                } else {
                    if (value.isFav) {
                        data[key].isFav = true
                    }
                    if (this.activeTabs.includes(filePath)) {
                        fileData.open = true
                    }
                }
            } else {
                let fileData = data[key]
                if (value.checkoutValue !== undefined && value.currentValue !== undefined &&
                    (value.checkoutValue != value.currentValue || value.pendingRemove)) {
                    if (value.pendingRemove) {
                        fileData.removed = true
                    } else {
                        fileData.modified = true
                    }
                    fileData.timestamp = value.currentTimestamp
                    if (value.checkoutHash != fileData.hash) {
                        fileData.outdate = true
                    }
                }
                if (!value.pendingRemove) {
                    if (value.isFav) {
                        fileData.isFav = true
                    }
                    if (this.activeTabs.includes(filePath)) {
                        fileData.open = true
                    }
                }
            }
        }
    }

    // TODO: remove files data that are not changed and not in tabs


}
