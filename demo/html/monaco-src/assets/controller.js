function iframeCall(iframe_id, data, origin) {
    iframe_obj = document.getElementById(iframe_id).contentWindow;
    if (iframe_obj === undefined) {
        return;
    }
    iframe_obj.postMessage({
        'func': 'call',
        'obj': data.obj,
        'method': data.method,
        'args': data.args,
        'callback': data.callback
    }, '*')
}

// Controller
class Controller {
    /* Coordinate objects according to happening events */

    editorCreated = false;
    editorDomain = null;

    browserCreated = false;
    browserDomain = null;

    remoteFiles = null;
    remoteData = null;
    localData = null;
    _started = 0;

    /*  TODO:
        x. Get Files list from server
        x. Store/Restore opened tabs list
        3. Editor Interactions
            - add tab
            - reaction to tab click
            - reaction to close tab (switch context then )
        x. Store additional info about files
            - hash
            - locks
        5. Save files on server
        6. Lock files on server
        7. Update preview
            - select displayed file
            - send local changes
            - all
            - opened tabs only
        8. Store actions on preview to update
    */

    /* TODO:
        op chains
        On Open
        - get domains list
        - restore domain
        - restore local data
        - update remote data (files hash, content of opened, not edited and remotely changes files etc.)
        - populate files browser (convert files info)
        - restore tabs
        - update preview

        Change domain
        - flush data
        - clean tabs
        - clean browser
        - change domain
        - repeat open

        Refresh
        - same as change domain
    */

    editorFrame = "editor"
    browserFrame = "browser"

    constructor(editorDomain, browserDomain, remoteFiles, remoteData, localData) {
        this.editorDomain = editorDomain;
        this.browserDomain = browserDomain;

        this.remoteFiles = remoteFiles;

        if (remoteData !== undefined) {
            this.remoteData = remoteData;
        }
        if (localData !== undefined) {
            this.localData = localData;
        }
    }

    attachData(remoteData, localData) {
        if ((this.remoteData !== null || this.localData !== null)) {
            throw Error("Data is already attached!")
        }
        this.remoteData = remoteData;
        this.localData = localData;
        this._start();
    }

    onEditorCreated() {
        this.editorCreated = true;
        console.log("Container: editor creation confirmed!");
        this._start()
    }

    onBrowserCreated() {
        this.browserCreated = true;
        console.log("Container: browser creation confirmed!");
        this._start()
    }

    editor = function(method, args, callback) {
        iframeCall(this.editorFrame, {
            "obj": "worker",
            "method": method,
            "args": args,
            "callback": callback
        }, this.editorDomain);
    }

    editorSettings = function(method, args, callback) {
        iframeCall(this.editorFrame, {
            "obj": "settings",
            "method": method,
            "args": args,
            "callback": callback
        }, this.editorDomain);
    }

    browser = function(method, args, callback) {
        iframeCall(this.browserFrame, {
            "obj": "browser",
            "method": method,
            "args": args,
            "callback": callback
        }, this.editorDomain);
    }

    _start() {
        // Don't start unless all start conditions are met
        if ((this.localData == null)
        || (this.remoteData == null)
        || (!this.editorCreated)
        || (!this.browserCreated)
        ) {
            return;
        }

        // Protect from coincident start
        if (++this._started != 1) {
            return;
        }

        let filesCount = 0; // Amount of locally saved files
        let lastFile = "";  // Last file is used to activate certain tab
        const localData = this.localData;

        // Load data into browser
        let filesData = {}
        this.remoteData.exportData("/", filesData)
        this.localData.exportData("/", filesData)
        this.browser("reload", [filesData])

        // Reopen tabs
        localData.activeTabs.forEach(key => {
            if ((localData.filesData[key] !== undefined) && (localData.filesData[key] !== null)) {
                this.editor("contextAdd", [key, localData.filesData[key].currentValue]);
                filesCount += 1;
                lastFile = key;
            }
        });

        // Try to activate tab that is in localData, otherwise last file from all tabs would be activated
        if (localData.filesData[localData.currentTab] !== undefined) {
            lastFile = localData.currentTab;
        }
        if (lastFile !== "") {
            this.editor("contextSwitch", [lastFile]);
        }

        // Subscribe to editor changes
        this.editorSettings("onChangeListenerSet", ["controller"]);

        /*
        NOTE: Welcome page, disabled
        if (filesCount === 0) {
            iframeCall("editor", {
                "obj": "worker",
                "method": "contextAdd",
                "args": ["hello.yaml", "hello: yaml4schm!"]
            }, this.editorDomain);

            iframeCall("editor", {
                "obj": "worker",
                "method": "contextSwitch",
                "args": ["hello.yaml"]
            }, this.editorDomain);

            localData.switchTab('hello.yaml');

            iframeCall("editor", {
                "obj": "worker",
                "method": "contextDump",
                "args": [],
                "callback": {
                    "func": "call",
                    "obj": "localData",
                    "method": "updateFilesAndTabs",
                }
            }, this.editorDomain);
        }
        */

    }

    onEditorChange(filePath) {
        console.warn("onEditorChange should be reworked!")
        return
        // TODO: this should be reworked since currently it's too heavy for simple reaction on editor changes
        this.localData.switchTab(filePath)
        // TODO: this most probably should be reworked
        this.editor("contextDump", [],
            {
                "func": "call",
                "obj": "localData",
                "method": "updateFilesAndTabs",
            })
        // TODO: schedule preview update after some time
    }

    onErrorsChange(info) {
        this.localData.updateProblemsEditor(info)
    }

    addTab(filePath) {
        return new Promise((resolve, reject) => {
            let fileContent = "";
            const remoteFiles = this.remoteFiles;
            const localData = this.localData;

            if (localData[filePath] === undefined) {
                // If there is not local data for this file path then get file from server
                remoteFiles.getFiles(localData.dataDomain, [filePath], ["content", "hash", "timestamp"])
                    .then(
                        (fileData) => {
                            if (fileData[filePath].content !== null) {
                                // File exists on server
                            } else {
                                // File not exists on server
                                fileData[filePath].content = "# A new file " + filePath;
                            }
                            return fileData[filePath];
                        }
                    )
                    .then(
                        (value) => {
                            fileContent = value.content;
                            return localData.addFile(
                                filePath,
                                value.content,
                                value.hash,
                                value.timestamp
                            )
                        }
                    )
            }
            if (localData[filePath] === undefined) {
                reject("Failed to get data from remote")
            }

            localData.addTab(filePath)
                .then(
                    () => {
                        return localData.switchTab(filePath)
                    }
                )
                .then(
                    () => {
                        iframeCall("editor", {
                            "obj": "worker",
                            "method": "contextAdd",
                            "args": [filePath, fileContent]
                        }, this.editorDomain);

                        iframeCall("editor", {
                            "obj": "worker",
                            "method": "contextSwitch",
                            "args": [filePath]
                        }, this.editorDomain);
                    }
                )
        })
    }

    switchTab(filePath) {
        this.localData.switchTab(filePath)
            .then(
                () => {
                    iframeCall("editor", {
                        "obj": "worker",
                        "method": "contextSwitch",
                        "args": [filePath]
                    }, this.editorDomain);
                },
                () => {
                    iframeCall("editor", {
                        "obj": "worker",
                        "method": "contextSwitch",
                        "args": [""]
                    }, this.editorDomain);
                }
            )
    }

    closeTab(filePath) {
        this.localData.removeTab(filePath)
            .then(
                (nextTab) => {
                    iframeCall("editor", {
                        "obj": "worker",
                        "method": "contextSwitch",
                        "args": [nextTab]
                    }, this.editorDomain);
                    iframeCall("editor", {
                        "obj": "worker",
                        "method": "contextRemove",
                        "args": [filePath]
                    }, this.editorDomain);
                },
                () => {
                    iframeCall("editor", {
                        "obj": "worker",
                        "method": "contextSwitch",
                        "args": [""]
                    }, this.editorDomain);
                    iframeCall("editor", {
                        "obj": "worker",
                        "method": "contextRemove",
                        "args": [filePath]
                    }, this.editorDomain);
                }
            )
    }

    dropFile(filePath) {
        this.localData.removeFile(filePath)
            .then(
                (nextTab) => {
                    iframeCall("editor", {
                        "obj": "worker",
                        "method": "contextSwitch",
                        "args": [nextTab]
                    }, this.editorDomain);
                    iframeCall("editor", {
                        "obj": "worker",
                        "method": "contextRemove",
                        "args": [filePath]
                    }, this.editorDomain);
                },
                () => {
                    iframeCall("editor", {
                        "obj": "worker",
                        "method": "contextSwitch",
                        "args": [""]
                    }, this.editorDomain);
                    iframeCall("editor", {
                        "obj": "worker",
                        "method": "contextRemove",
                        "args": [filePath]
                    }, this.editorDomain);
                }
            )
    }

    serverSync() {
        // TODO:
    }

    editorSync() {
        // TODO:
    }

}
