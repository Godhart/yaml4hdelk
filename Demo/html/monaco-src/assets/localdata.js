class FileData {
    /* Class to store misc file related data */
    currentValue = ""   // Current value
    problemsEditor = 0  // Amount of problems detected by editor
    problemsRemote = 0  // Amount of problems detected by server
    source = null       // Initial value, that were received from server on checkout
    source_timestamp = 0// Initial value timestamp, that were received from server on checkout
    source_hash = null  // Hash that were received from server on checkout
    timestamp = 0       // Last modification timestamp
}


class LocalData {
    /* Local data storage */

    session = null      // Current session timestamp. Used to understand if session is outdated
                        // (detect if another session were opened on other browser tab)
    filesData = {}      // Dict with file data. Key is file path, value is FileData instance
    activeTabs = []     // List of active tabs, that should be displayed in editor. Value is file path
    currentTab = ""     // Currently selected tab. Value is file path
    dataDomain = ""     // Current data domain
    co = {}

    constructor(fallbackDomain) {
        if (dataDomain === undefined) {
            this._restore("yaml4schm-monaco-domain")
            .then(
                (domain)    => { dataDomain = domain },
                ()          => { dataDomain = fallbackDomain}
            )
        }
        this.switchDomain(dataDomain);
    }

    switchDomain(dataDomain) {
        // Switches current active domain to work with
        if (this.dataDomain !== "") {
            this.storeAll();
        }
        if (this.session !== null) {
            this.releaseSession();
        }
        this.dataDomain = dataDomain;
        this._store("yaml4schm-monaco-domain", dataDomain);
        this.co = {
            "session": "yaml4schm-monaco-" + dataDomain + "-session",
            "filesData": "yaml4schm-monaco-" + dataDomain + "-filesData",
            "currentTab": "yaml4schm-monaco-" + dataDomain + "-currentTab",
            "activeTabs": "yaml4schm-monaco-" + dataDomain + "-activeTabs",
        }
        this.newSession()
            .then(
                (session) => { return this.reload() }
            )
    }

    _store(key, value) {
        return new Promise((resolve, reject) => {
            if (JSON.parse(localStorage.getItem(this.co.session)) === this.session) {
                localStorage.setItem(this.co[key], JSON.stringify(value));
                resolve("Success!")
            } else {
                reject("Session changed")
            }
        })
    }

    _restore(key) {
        return new Promise((resolve, reject) => {
            if (localStorage.getItem(this.co.session) === this.session) {
                let value = localStorage.getItem(this.co[key]);
                if (value) {
                    resolve(JSON.parse(value))
                } else {
                    reject(undefined)
                }
            } else {
                reject(null)
            }
        })
    }

    newSession() {
        return new Promise((resolve, reject) => {
            this.session = new Date().getTime()
            localStorage.setItem(this.co.session, JSON.stringify(this.session));
            // TODO: ask if it"s ok to drop previous session
            resolve(this.session)
        })
    }

    releaseSession() {
        return new Promise((resolve, reject) => {
            this._store(this.co.session, null)
                .then(
                    () => { this.session = null; resolve("Success!") },
                    () => { this.session = null; resolve("Session changed!") }
                )
        })
    }

    reload() {
        return new Promise((resolve, reject) => {
            this.filesData = {};
            this.activeTabs = [];
            this.currentTab = "";

            this._restore(this.co.filesData)
                .then(
                    (data) => {
                        this.filesData = {};
                        for (const [key, value] of Object.entries(data)) {
                            this.filesData[key] = Object.assign(new FileData(), value);
                        }
                    },
                    (value) => {
                        if (value === undefined) {
                            //
                        } else {
                            reject("Session changed!");
                        }
                    }
                );

            this._restore(this.co.activeTabs)
                .then(
                    (activeTabs) => {
                        activeTabs.forEach(tab => {
                            if (this.filesData[tab] !== undefined) {
                                this.activeTabs.push(tab);
                            }
                        })
                    },
                    (value) => {
                        if (value === undefined) {
                            //
                        } else {
                            reject("Session changed!");
                        }
                    }
                )

            this._restore(this.co.currentTab)
                .then(
                    (currentTab) => { this.currentTab = currentTab },
                    (value) => {
                        if (value === undefined) {
                            //
                        } else {
                            reject("Session changed!");
                        }
                    }
                )

            if (!this.activeTabs.includes(this.currentTab)) {
                if (this.activeTabs.length > 0) {
                    this.currentTab = this.activeTabs[0];
                } else {
                    this.currentTab = "";
                }
            }

            resolve("Success");
        })
    }

    storeAll() {
        return new Promise((resolve, reject) => {
            this._store(this.co.filesData, this.filesData)
                .then(
                    () => { return this._store(this.co.activeTabs, this.activeTabs) },
                    () => { reject("Session changed!"); }
                )
                .then(
                    () => { return this._store(this.co.currentTab, this.currentTab) },
                    () => { reject("Session changed!"); }
                )
                .then(
                    () => resolve("Success!"),
                    () => { reject("Session changed!"); }
                )
        })
    }

    addFile(filePath, source, hash, timestamp) {
        return new Promise((resolve, reject) => {
            if (this.filesData[filePath] === undefined) {
                this.filesData[filePath] = Object.assign(new FileData(), {
                    "currentValue": source,
                    "source": source,
                    "source_timestamp": timestamp,
                    "source_hash": hash,
                    "timestamp": timestamp,
                });
                this._store(this.co.filesData, this.filesData)
                    .then(
                        () => { resolve("Success") },
                        () => { reject("Session changed!") }
                    )
            } else {
                console.error("LocalData.addFile(): File " + filePath + " is already in database");
                reject("File " + filePath + " is already in database");
            }
        })
    }

    addTab(filePath) {
        return new Promise((resolve, reject) => {
            if (this.filesData[filePath] !== undefined) {
                if (this.activeTabs.includes(filePath)) {
                    console.error("LocalData.addTab(): Tab is already in list");
                    reject("Tab is already in list");
                } else {
                    this.activeTabs.push(filePath);
                    this._store(this.co.activeTabs, this.activeTabs)
                        .then(
                            () => { resolve("Success") },
                            () => { reject("Session changed!") }
                        )
                }
            } else {
                console.error("LocalData.addTab(): No file " + filePath + " for tab in database");
                reject("No file " + filePath + " for tab in database");
            }
        })
    }

    updateFileStatics(filePath, source, hash, timestamp) {
        return new Promise((resolve, reject) => {
            if (this.filesData[filePath] !== undefined) {
                let f = this.filesData[filePath];
                if (source !== undefined && source !== null) {
                    f.source = source
                }
                if (hash !== undefined && hash !== null) {
                    f.source_hash = hash
                }
                if (timestamp !== undefined && hash !== null) {
                    f.source_timestamp = timestamp
                }
                this._store(this.co.filesData, this.filesData)
                    .then(
                        () => { resolve("Success") },
                        () => { reject("Session changed!") }
                    )
            } else {
                console.error("LocalData.updateFileStatics(): File " + filePath + "is not in database");
                reject("File " + filePath + " is not in database");
            }
        })
    }

    updateFileValue(filePath, value) {
        return new Promise((resolve, reject) => {
            if (this.filesData[filePath] !== undefined) {
                let f = this.filesData[filePath];
                f.currentValue = value;
                f.timestamp = new Date().getTime();
                this._store(this.co.filesData, this.filesData)
                    .then(
                        () => { resolve("Success") },
                        () => { reject("Session changed!") }
                    )
            } else {
                console.error("LocalData.updateFileValue(): File " + filePath + "is not in database");
                reject("File " + filePath + " is not in database");
            }
        })
    }

    removeFile(filePath) {
        return new Promise((resolve, reject) => {
            if (this.filesData[filePath] !== undefined) {
                this.removeTab(filePath);
                delete this.filesData[filePath];
                this._store(this.co.filesData, this.filesData)
                    .then(
                        () => { resolve(this.currentTab) },
                        () => { reject("Session changed!") }
                    )
            } else {
                console.error("LocalData.removeFile(): File " + filePath + "is not in database");
                reject("File " + filePath + " is not in database");
            }
        })
    }

    removeTab(filePath) {
        return new Promise((resolve, reject) => {
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
            this._store(this.co.activeTabs, this.activeTabs)
                .then(
                    () => { return this._store(this.co.currentTab, this.currentTab) },
                    () => { reject("Session changed!") }
                )
                .then(
                    () => { resolve(this.currentTab) },
                    () => { reject("Session changed!") }
                )
        })
    }

    switchTab(filePath) {
        return new Promise((resolve, reject) => {
            if (this.filesData[filePath] !== undefined) {
                this._store(this.co.currentTab, filePath)
                    .then(
                        () => { this.currentTab = filePath; resolve("Success") },
                        () => { reject("Session changed!") }
                    )
            } else {
                console.error("LocalData.currentTabSet(): File " + filePath + " is not in database");
                reject("File " + filePath + " is not in database");
            }
        });
    }

    updateFilesAndTabs(data) {
        return new Promise((resolve, reject) => {
            this.activeTabs = []
            for (const [key, value] of Object.entries(data)) {
                if (this.filesData[key] === undefined) {
                    this.filesData[key] = new FileData();
                }
                this.activeTabs.push(key);
                this.filesData[key].currentValue = value;
            }
            if (!this.activeTabs.includes(this.currentTab)) {
                if (this.activeTabs.length > 0) {
                    this.currentTab = this.activeTabs[0]
                } else {
                    this.currentTab = "";
                }
            }
            this._store(this.co.filesData, this.filesData)
                .then(
                    () => { return this._store(this.co.activeTabs, this.activeTabs) },
                    () => { reject("Session changed!") }
                )
                .then(
                    () => { resolve("Success") },
                    () => { reject("Session changed!") }
                )
        });
    }

    updateProblemsEditor(data) {
        return new Promise((resolve, reject) => {
            const filePath = data.path.substring(1);
            if (this.filesData[filePath] !== undefined) {
                this.filesData[filePath].problemsEditor = data.problemsCount;
                this._store(this.co.filesData, this.filesData)
                    .then(
                        () => { resolve("Success") },
                        () => { reject("Session changed!") }
                    )
            }
            console.error("LocalData.updateProblemsEditor(): File " + data.path + " is not in database");
            reject("File " + data.path + " is not in database");
        });
    }

    updateProblemsRemote(data) {
        return new Promise((resolve, reject) => {
            const filePath = data.filePath;
            if (this.filesData[filePath] !== undefined) {
                this.filesData[filePath].problemsRemote = data.problemsCount;
                this._store(this.co.filesData, this.filesData)
                    .then(
                        () => { resolve("Success") },
                        () => { reject("Session changed!") }
                    )
            }
            console.error("LocalData.updateProblemsRemote(): File " + data.path + " is not in database");
            reject("File " + data.path + " is not in database");
        })
    }

}
