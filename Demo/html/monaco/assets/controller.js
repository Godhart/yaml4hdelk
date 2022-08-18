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
    editorCreated = false;
    editorDomain = null;
    remoteFiles = null;

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

    constructor(remoteFiles, editorDomain) {
        this.remoteFiles = remoteFiles;
        this.editorDomain = editorDomain;
    }

    onEditorCreated() {
        this.editorCreated = true;
        console.log("Container: editor creation confirmed!");

        // Reopen tabs
        let filesCount = 0; // Amount of locally saved files
        let lastFile = "";  // Last file is used to activate certain tab
        localData.activeTabs.forEach(key => {
            if ((localData.filesData[key] !== undefined) && (localData.filesData[key] !== null)) {
                iframeCall("editor", {
                    "obj": "worker",
                    "method": "contextAdd",
                    "args": [key, localData.filesData[key].currentValue]
                }, this.editorDomain);
                filesCount += 1;
                lastFile = key;
            }
        });

        // Try to activate tab that is in localData, otherwise last file from all tabs would be activated
        if (localData.filesData[localData.currentTab] !== undefined) {
            lastFile = localData.currentTab;
        }
        if (lastFile !== "") {
            iframeCall("editor", {
                "obj": "worker",
                "method": "contextSwitch",
                "args": [lastFile]
            }, this.editorDomain);
        }

        // Subscribe to editor changes
        iframeCall("editor", {
            "obj": "settings",
            "method": "onChangeListenerSet",
            "args": ["controller"]
        }, this.editorDomain);

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
        localData.switchTab(filePath)
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
        // TODO: schedule preview update after some time
    }

    onErrorsChange(info) {
        localData.updateProblemsEditor(info)
    }

    addTab(filePath) {
        return new Promise((resolve, reject) => {
            let fileContent = "";
            if (this.localData[filePath] === undefined) {
                this.remoteFiles.getFile(filePath)
                    .then(
                        (fileData) => {
                            if (fileData.content !== null) {
                                // File exists on server
                            } else {
                                // File not exists on server
                                fileData.content = "# A new file " + filePath;
                            }
                            return fileData;
                        }
                    )
                    .then(
                        (value) => {
                            fileContent = value.content;
                            return this.localData.addFile(
                                filePath,
                                value.content,
                                value.hash,
                                value.lock
                            )
                        }
                    )
            }
            if (this.localData[filePath] === undefined) {
                reject("Failed to get data from remote")
            }

            this.localData.addTab(filePath)
                .then(
                    () => {
                        return this.localData.switchTab(filePath)
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
