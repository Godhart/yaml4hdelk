class FileData {
    problemsEditor = 0
    problemsRemote = 0
    stateInitial = null
    currentValue = ""
}

class LocalData {
    localChanges = {}
    lastActiveFile = ''
    dataDomain = ''
    co = {}

    constructor(dataDomain) {
        this.dataDomain = dataDomain;
        this.co = {
            'localChanges': 'yaml4schm-monaco-localChanges-'+dataDomain,
            'activeFile': 'yaml4schm-monaco-activeFile-'+dataDomain,
        }

        const storedChanges = localStorage.getItem(this.co.localChanges);
        if (storedChanges) {
            console.log("Loading stored changes:" + storedChanges);
            this.localChanges = {};
            const data = JSON.parse(storedChanges);
            for (const [key, value] of Object.entries(data)) {
                this.localChanges[key] = Object.assign(new FileData(), value);
            }
        }
        const activeFile = localStorage.getItem(this.co.activeFile);
        if (activeFile) {
            this.lastActiveFile = activeFile;
        }
    }

    lastActiveFileSet(value) {
        if (this.localChanges[value] !== undefined) {
            this.lastActiveFile = value;
            localStorage.setItem(this.co.activeFile, this.lastActiveFile);
            console.log(this.lastActiveFile);
        }
    }

    updateAll(data) {
        for (const [key, value] of Object.entries(data)) {
            if (this.localChanges[key] === undefined) {
                this.localChanges[key] = new FileData();
            }
            this.localChanges[key].currentValue = value;
            localStorage.setItem(this.co.localChanges, JSON.stringify(this.localChanges));
        }
        console.log(JSON.stringify(this.localChanges));
    }

    updateErrors(data) {
        const filePath = data.path.substring(1);
        if (this.localChanges[filePath] !== undefined) {
            this.localChanges[filePath].problemsEditor = data.problemsCount;
            localStorage.setItem(this.co.localChanges, JSON.stringify(this.localChanges));
            console.log(JSON.stringify(this.localChanges));
        }
    }

}
