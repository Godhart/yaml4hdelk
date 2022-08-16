function iframe_call(iframe_id, data, origin) {
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
    serverTalk = null;

    /*  TODO:
        1. Get Files list from server
        2. Store opened tabs list
        3. Editor Interactions
            - add tab
            - reaction to tab click
            - reaction to close tab (switch context then )
        4. Store additional info about files
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

    constructor(serverTalk, editorDomain) {
        this.serverTalk   = serverTalk;
        this.editorDomain = editorDomain;
    }

    updateFilesList() {

    }

    onEditorCreated() {
        this.editorCreated = true;
        console.log("Container: editor creation confirmed!");

        let filesCount = 0;
        let lastFile = '';
        for (const [key, value] of Object.entries(localData.localChanges)) {
            iframe_call("editor", {
                "obj": "worker",
                "method": "contextAdd",
                "args": [key, value.currentValue]
            }, this.editorDomain);
            filesCount += 1;
            lastFile = key;
        }

        if (localData.localChanges[localData.lastActiveFile] !== undefined) {
            lastFile = localData.lastActiveFile;
        }
        if (lastFile !== "") {
            iframe_call("editor", {
                "obj": "worker",
                "method": "contextSwitch",
                "args": [lastFile]
            }, this.editorDomain);
        }

        iframe_call("editor", {
            "obj": "settings",
            "method": "onChangeListenerSet",
            "args": ["controller"]
        }, this.editorDomain);

        if (filesCount === 0) {
            iframe_call("editor", {
                "obj": "worker",
                "method": "contextAdd",
                "args": ["hello.yaml", "hello: yaml4schm!"]
            }, this.editorDomain);

            iframe_call("editor", {
                "obj": "worker",
                "method": "contextSwitch",
                "args": ["hello.yaml"]
            }, this.editorDomain);

            localData.lastActiveFileSet('hello.yaml');

            iframe_call("editor", {
                "obj": "worker",
                "method": "contextDump",
                "args": [],
                "callback": {
                    "func": "call",
                    "obj": "localData",
                    "method": "updateAll",
                }
            }, this.editorDomain);
        }
    }

    onEditorChange(filePath) {
        localData.lastActiveFileSet(filePath)
        // TODO: schedule update after some time
        // TODO: update preview
        iframe_call("editor", {
            "obj": "worker",
            "method": "contextDump",
            "args": [],
            "callback": {
                "func": "call",
                "obj": "localData",
                "method": "updateAll",
            }
        }, this.editorDomain);
    }

    onErrorsChange(info) {
        localData.updateErrors(info)
    }
}
