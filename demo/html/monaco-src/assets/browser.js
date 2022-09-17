// Constants for graphics symbols
// This one are just for reference
const Add = "&#128932;"
const Eye = "&#128065;"
const Star = "&#9733;"
const Pencil = "&#128393;"
const Lock = "&#9919;"
const CollapsedFolder = "&#128448;"
const ExpandedFolder = "&#128449;"
const Save = "&#128427;"
const Delete = "&#10005;"
const Reset = "&#9100;"
const Warning = "&#9888;"
const Stop = "&#11203;"
const Reload = "&#10226;"
const DocText = "&#128441;"
const DocPic = "&#128443;"
const Circle = "&#9679;"
const Link = "&#11179;"

// All the possible file statuses except errors
const fileStatus = ["outdate", "flocked", "locked", "added", "modified", "removed", "renamed",]
// TODO: outdate, flocked, locked are custom and should be specified on per instance basis

// Statues that are indicating that file data changed
const fileStatusChanged = ["added", "modified", "removed", "renamed",]
// TODO: may be customized in the future

// Mnemonic constants for path pattern matching
const PathStartsWidth = 0
const PathContains = 1
const PathAny = -1

// View related constants
const filterSet = {
    "full": ["locked", "flocked", "open", "fav", "outdate", "errors", "changed"],
    "compact": ["fav", "errors", "open", "changed"],
    "tiny": ["changed", "open"]
}
// TODO: outdate, flocked, locked are custom and should be specified on per instance basis

const filterStraight = {
    "full": ["locked", "flocked", "open", "fav", "outdate"],
    "compact": ["fav", "open"],
    "tiny": ["open"]
}
// TODO: outdate, flocked, locked are custom and should be specified on per instance basis

const views = ["tiny", "compact", "full"]

class Browser {
    filez = {}
    folders = {}
    filesFilter = {}
    view = "tiny"
    uiFeedback = ""

    // IDs to reference HTML items.
    // Could be overriden on per instance basis
    filePathFilterId = "filePathFilter"
    filtersRowId = "filtersRow"
    filesBrowserId = "filesBrowser"
    filesListId = "filesList"

    constructor(filterCommonFields, view, uiFeedback) {
        this.uiFeedback = uiFeedback
        this.filesFilter = {
            "pathRoot": "",
            "path": "",
            "changed": undefined,
            "fav": undefined,
            "open": undefined,
            "errors": undefined,
            /*  NOTE: this one are considered custom and should be added via filterCommonFields
                "locked": undefined,
                "flocked": undefined,
                "outdate": undefined,
           */
            "folders": undefined,
            "union": true,
        }
        if (filterCommonFields !== undefined) {
            for (const [field, defaultValue] of Object.entries(filterCommonFields)) {
                this.filesFilter[field] = defaultValue
            }
        }
        if (view !== undefined) {
            if (views.includes(view)) {
                this.view = view
            } else {
                this.view = "tiny"
            }
        }
    }

    reload(filez) {
        this.filez = filez
        this.folders = {}

        document.getElementById(this.filesListId).innerHTML=""
        this.populate(document.getElementById(this.filesBrowserId))
        this.update()
    }

    getFilterRow = function () {
        return document.getElementById(this.filtersRowId)
    }

    toggleFolder = function (path) {
        if (this.folders[path].expanded) {
            this.folders[path].expanded = false
        } else {
            this.folders[path].expanded = true
        }
        this.refreshView(this.filez, this.folders, this.filesFilter)
    }

    toggleAllFolder = function () {
        const fr = this.getFilterRow()
        let expanded = fr.getAttribute("data-folder-expanded") == "true"
        expanded = !expanded
        this.toggleFolderExpanded(expanded)
        fr.setAttribute("data-folder-expanded", "" + expanded)
        this.refreshView(this.filez, this.folders, this.filesFilter)
    }

    toggleFolderExpanded = function (expanded) {
        for (const [folderPath, value] of Object.entries(this.folders)) {
            value.expanded = expanded
        }
    }

    toggleFolderFilter = function (path) {
        const filter = document.getElementById(this.filePathFilterId)
        if (this.filesFilter.pathRoot == path) {
            this.filesFilter.pathRoot = ""
        } else {
            this.filesFilter.pathRoot = path
        }
        filter.value = ""
        this.updatePathFilter(filter.value)
    }

    toggleFilter = function (filterField, filterAttribute) {
        const fr = this.getFilterRow()
        let value = fr.getAttribute(filterAttribute) == "true"
        value = !value
        if (value) {
            this.filesFilter[filterField] = true
        } else {
            this.filesFilter[filterField] = undefined
        }
        fr.setAttribute(filterAttribute, "" + value)
        this.updateFilter(this.filez, this.folders, this.filesFilter)
    }

    populate = function (elTable) {
        // Reads data from this.filez (that were set via constructor)
        // and adds corresponding data into this.folders and onto HTML

        // TODO: a way to customize toolbox and statuses
        // lock, flock, outdate in this case

        const table = elTable
        const filez = this.filez
        const folders = this.folders
        const foldersList = []

        for (const [filePath, value] of Object.entries(filez)) {
            value.path = filePath
            value.id = "file-" + filePath
            value.visible = true

            let folderPath = filePath.split('/').slice(0, -1).join('/')
            let folder = null
            if (folders[folderPath] === undefined) {
                folders[folderPath] = {
                    "path": folderPath, "id": "folder-" + folderPath,
                    "filez": {}, "folders": {}, "folder": null, visible: true, "expanded": false
                }
                if (folderPath == "") {
                    folders[folderPath].expanded = true
                }
                foldersList.push(folderPath)
                folder = folders[folderPath]
                // Add folder row
                if (folderPath != "") {
                    let folderRow = table.insertRow()
                    folder.row = folderRow
                    folderRow.setAttribute("data-folder", "true")
                    folderRow.setAttribute("data-path", folderPath)
                    folderRow.classList.add("shown")
                    folderRow.id = folder.id + "-row"
                    let cell = null

                    cell = folderRow.insertCell()
                    cell.innerHTML = '<button id="' + folder.id + '-icon" title="Collapse/Expand" class="tool-icon f-theme tool-icon-folder" onclick="' + this.uiFeedback + '.toggleFolder(this)"></button>'

                    cell = folderRow.insertCell()
                    let folderName = folderPath.split("/").slice(-1)
                    let folderLocation = folderPath.split("/").slice(0, -1).join("/") + "/"
                    let folderMargin = folderPath.split("/").length - 2
                    let folderMarginContent = ""
                    for (let i = 0; i < folderMargin; i++) {
                        folderMarginContent += "M"
                    }

                    cell.innerHTML =
                        '<button id="' + folder.id + '-main" title="Click to change focus\nFull path: ' + folderPath + '"\
class="tool b-t tool-status-color" onclick="' + this.uiFeedback + '.toggleFolderFilter(this)">\
<span class="path-margin">'+ folderMarginContent + '</span>\
<span class="path-location">' + folderLocation + '</span><span>' + folderName + '</span></button>'
                    // TODO: +   '<button id="' + folder.id + '-enter" title="Enter folder" class="tool bf-t tool-folder-entry" onclick="enterFolder(this)">&#8628;</button>'

                    cell = folderRow.insertCell()
                    cell.innerHTML = '<button id="' + folder.id + '-status" title="Status" class="tool tool-f-status tool-status-color""></button>'
                    folder.stat_but = document.getElementById(folder.id + "-status")

                    cell = folderRow.insertCell()
                    cell.id = folder.id + "-nodeOps"
                    cell.innerHTML = "<span class='node-info'>\
<button class='tool tool-f-added'>A</button>\
<button class='tool tool-f-modified'>M</button>\
<button class='tool tool-f-renamed'>R</button>\
<button class='tool tool-f-removed'>D</button>\
</span>\
<span   id='" + folder.id + "-toolbox' class='toolbox'>" + '\
<button id="' + folder.id + '-add"     class="tool-icon x-add     " title="Add"              onclick="' + this.uiFeedback + '.addNode(this)">&#128932;</button>\
<button id="' + folder.id + '-delete"  class="tool-icon x-delete  " title="Remove Folder"    onclick="' + this.uiFeedback + '.deleteNode(this)">&#10005;</button>\
<button id="' + folder.id + '-rename"  class="tool-icon x-rename  " title="Move/Rename"      onclick="' + this.uiFeedback + '.renameNode(this)">&#128393;</button>\
<button id="' + folder.id + '-save"    class="tool-icon x-save    " title="Save changes"     onclick="' + this.uiFeedback + '.saveChanges(this)">&#128427;</button>\
<button id="' + folder.id + '-reset"   class="tool-icon x-reset   " title="Reset changes"    onclick="' + this.uiFeedback + '.resetChanges(this)"></button>\
<button id="' + folder.id + '-lock"    class="tool-icon x-lock    " title="Lock"             onclick="' + this.uiFeedback + '.lockNode(this)">&#9919;</button>\
' + "</span>"

                    cell = folderRow.insertCell()
                    cell.innerHTML = '\
<button id="' + folder.id + '-fav"     class="tool-icon tool-fav     " title="Favorite"         onclick="' + this.uiFeedback + '.favNode(this)">&#9733;</button>'
                    folder.fav_cell = cell

                    cell = folderRow.insertCell()
                    cell.innerHTML = '\
<button id="' + folder.id + '-error"   class="tool-icon tool-error   " title="Errors"        onclick="' + this.uiFeedback + '.showNodeErrors(this)">&#9888;</button>'
                    folder.err_but = document.getElementById(folder.id + "-error")

                    cell = folderRow.insertCell()
                }
            } else {
                folder = folders[folderPath]
            }

            value.folder = folder
            folder.filez[filePath] = value

            // Add file row
            let fileRow = table.insertRow()
            value.row = fileRow
            fileRow.setAttribute("data-file", "true")
            fileRow.setAttribute("data-path", filePath)
            fileRow.classList.add("shown")
            fileRow.id = value.id + "-row"
            let cell = null

            cell = fileRow.insertCell()
            cell.innerHTML = '<button id="' + value.id + '-icon" title="Focus Tab" class="tool-icon f-theme tool-icon-file" onclick="' + this.uiFeedback + '.focusTab(this)"></button>'

            cell = fileRow.insertCell()
            let fileName = filePath.split("/").slice(-1)
            let fileLocation = filePath.split("/").slice(0, -1).join("/") + "/"
            let fileMargin = filePath.split("/").length - 2
            let fileMarginContent = ""
            for (let i = 0; i < fileMargin; i++) {
                fileMarginContent += "M"
            }

            cell.innerHTML =
                '<button id="' + value.id + '-main" title="Click to toggle Tab\nFull path: ' + filePath + '"\
class="tool b-t tool-text tool-status-color" onclick="' + this.uiFeedback + '.toggleTab(this)">\
<span class="path-margin">'+ fileMarginContent + '</span>\
<span class=path-location>' + fileLocation + '</span><span>' + fileName + '</span></button>'

            cell = fileRow.insertCell()
            cell.innerHTML = '<button id="' + value.id + '-status" title="Status" class="tool tool-status tool-status-color""></button>'
            value.stat_but = document.getElementById(value.id + "-status")

            cell = fileRow.insertCell()
            cell.id = value.id + "-nodeOps"
            cell.innerHTML = "<span class='node-info f-greyed'>" + new Date(value.timestamp).toLocaleString() + "</span>\
<span   id='" + value.id + "-toolbox' class='toolbox'>" + '\
<button id="' + value.id + '-add"     class="tool-icon x-add     " title="Add"              onclick="' + this.uiFeedback + '.addNode(this)">&#128932;</button>\
<button id="' + value.id + '-delete"  class="tool-icon x-delete  " title="Remove"           onclick="' + this.uiFeedback + '.deleteNode(this)">&#10005;</button>\
<button id="' + value.id + '-rename"  class="tool-icon x-rename  " title="Move/Rename"      onclick="' + this.uiFeedback + '.renameNode(this)">&#128393;</button>\
<button id="' + value.id + '-save"    class="tool-icon x-save    " title="Save changes"     onclick="' + this.uiFeedback + '.saveChanges(this)">&#128427;</button>\
<button id="' + value.id + '-reset"   class="tool-icon x-reset   " title="Reset changes"    onclick="' + this.uiFeedback + '.resetChanges(this)"></button>\
<button id="' + value.id + '-lock"    class="tool-icon x-lock    " title="Lock"             onclick="' + this.uiFeedback + '.lockNode(this)">&#9919;</button>\
' + "</span>"

            cell = fileRow.insertCell()
            cell.innerHTML = '\
<button id="' + value.id + '-fav"     class="tool-icon tool-fav     " title="Favorite"      onclick="' + this.uiFeedback + '.favNode(this)">&#9733;</button>'
            value.fav_cell = cell

            cell = fileRow.insertCell()
            cell.innerHTML = '\
<button id="' + value.id + '-error"   class="tool-icon tool-error   " title="Errors"        onclick="' + this.uiFeedback + '.showNodeErrors(this)">&#9888;</button>'
            value.err_but = document.getElementById(value.id + "-error")

            cell = fileRow.insertCell()
            cell.innerHTML = '\
<button id="' + value.id + '-link"    class="tool-icon tool-link    " title="Open Schematic" onclick="' + this.uiFeedback + '.openNodeLink(this)">&#11179;</button>'
        }

        // After all folders are populated it's time to link subfolders to their parents
        foldersList.forEach(folderPath => {
            let parentPath = folderPath
            while (parentPath.length > 0) {
                parentPath = parentPath.split('/').slice(0, -1).join('/')
                if (folders[parentPath] == undefined) {
                    continue
                }
                folders[folderPath].folder = folders[parentPath]
                folders[parentPath].folders[folderPath] = folders[folderPath]
                break
            }
        })
    }

    parentIsCollapsed = function (node, filters) {
        if (node.folder == null) {
            return false;
        } else {
            if (filters.pathRoot == node.folder.path || (filters.path.length > 0 && filters.path[0] != "/")) {
                return false;
            } else if (!node.folder.expanded) {
                return true;
            } else {
                return this.parentIsCollapsed(node.folder, filters)
            }
        }
    }

    updateAttributes = function (filez, folders) {
        // Reset then update folder statuses
        for (const [folderPath, value] of Object.entries(folders)) {
            value.attributes = { "status": {}, "folder-expanded": "true", "fav": "folder", "errors": [], "modified": [] }
            // Apply expanded property only, other are defined by files
            if (!value.expanded) {
                value.attributes["folder-expanded"] = "false"
            }
        }
        // Reset then update files statuses and statuses of their folders
        for (const [filePath, value] of Object.entries(filez)) {
            value.attributes = { "status": {}, "file-open": "false", "fav": "false", "errors": [] }
            if (value.open) {
                value.attributes["file-open"] = "true"
            }
            if (value.fav) {
                value.attributes.fav = "true"
                value.folder.attributes.fav = "true"
            }
            let ch = false
            fileStatus.forEach(stat => {
                if (value[stat]) {
                    value.attributes.status[stat] = true
                    value.folder.attributes.status[stat] = true
                    if (!ch && fileStatusChanged.indexOf(stat) >= 0) {
                        ch = true
                        value.attributes.status["changes"] = true
                        value.folder.attributes.status["changes"] = true
                        value.folder.attributes.modified.push(filePath)
                    }
                }
            })
            let err = false
            if (value.errors !== undefined && value.errors !== null && value.errors.length > 0) {
                value.attributes.status.errors = true
                value.folder.attributes.status.errors = true
                value.attributes.errors = value.attributes.errors.concat(value.errors)
                value.folder.attributes.errors.push(filePath)
                err = true
            }
            if (value.outdate) {
                value.attributes.status.errors = true
                value.folder.attributes.status.errors = true
                value.attributes.errors.push("Source changed on server")
                if (!err) {
                    value.folder.attributes.errors.push(filePath)
                }
            }
        }
        // Propagate folder's statuses to parents
        // Start from leaf folders
        let currentFolders = []
        for (const [folderPath, value] of Object.entries(folders)) {
            if ((Object.keys(value.folders)).length > 0) {
                // skip non leaf folders
                continue
            }
            currentFolders.push(value)
        }
        // Walk up to the root aggregating stats along the way
        while (currentFolders.length > 0) {
            let parentFolders = []
            currentFolders.forEach(current => {
                let parent = current.folder
                if (parent !== undefined && parent !== null) {

                    fileStatus.forEach(stat => {
                        if (current.attributes.status[stat]) {
                            parent.attributes.status[stat] = true
                        }
                    })
                    if (current.attributes.fav == "true") {
                        if (parent.attributes.fav == "folder") {
                            parent.attributes.fav = "nested"
                        }
                    }
                    if (current.attributes.errors.length > 0) {
                        parent.attributes.errors = parent.attributes.errors.concat(current.attributes.errors)
                    }
                    parentFolders.push(current.folder)
                }
            })
            currentFolders = parentFolders
        }
    }

    applyAttributes = function (node) {
        if (node.row === undefined && node.row === null) {
            return
        }
        if (node.attributes !== undefined) {
            for (const [attr, value] of Object.entries(node.attributes)) {
                if (attr == "status") {
                    node.row.setAttribute("data-status", Object.keys(value).join(" "))
                    node.stat_but.title = Object.keys(value).join("\n") // TODO: describe status better
                } else if (attr == "errors") {
                    if (value.length > 0) {
                        node.row.setAttribute("data-errors", "true")
                        node.err_but.title = value.join("\n")
                    } else {
                        node.row.setAttribute("data-errors", "false")
                    }
                } else if (attr == "modified") {
                    node.stat_but.title = value.join("\n")
                } else {
                    node.row.setAttribute("data-" + attr, value)
                }
                if (node.attributes.fav == "false") {
                    node.fav_cell.classList.add("no-fav")
                } else {
                    node.fav_cell.classList.remove("no-fav")
                }
            }
        }
    }

    refreshView = function (filez, folders, filters) {
        this.updateAttributes(filez, folders)
        for (const [filePath, value] of Object.entries(filez)) {
            if (!value.visible || (!filters.folders && (!value.folder.visible || this.parentIsCollapsed(value, filters)))) {
                value.row.classList.add("hidden")
                value.row.classList.remove("shown")
            } else {
                value.row.classList.add("shown")
                value.row.classList.remove("hidden")
                this.applyAttributes(value)
            }
        }
        for (const [folderPath, value] of Object.entries(folders)) {
            if (value.row !== undefined) {
                if ((filters.folders || !value.visible || this.parentIsCollapsed(value, filters)) && filters.pathRoot != value.path) {
                    value.row.classList.add("hidden")
                    value.row.classList.remove("shown")
                } else {
                    value.row.classList.add("shown")
                    value.row.classList.remove("hidden")
                    this.applyAttributes(value)
                }
            }
        }
    }

    pathMatch = function (matchType, path, pattern) {
        return matchType == PathAny
            || (matchType == PathStartsWidth && path.startsWith(pattern.substring(1)))
            || (matchType == PathContains && path.search(pattern) >= 0)
    }

    toggleView = function (value) {
        if (value === undefined) {
            if (this.view == "tiny") {
                this.view = "compact"
            } else if (this.view == "compact") {
                this.view = "full"
            } else {
                this.view = "tiny"
            }
        } else {
            if (views.includes(value)) {
                this.view = value
            } else {
                return this.view
            }
        }
        let t = document.getElementById(this.filesBrowserId)
        if (this.view == "full") {
            t.classList.add("tool-full")
            t.classList.remove("tool-tiny")
            t.classList.remove("tool-compact")
        } else if (this.view == "compact") {
            t.classList.add("tool-compact")
            t.classList.remove("tool-tiny")
            t.classList.remove("tool-full")
        } else {
            t.classList.add("tool-tiny")
            t.classList.add("tool-compact")
            t.classList.remove("tool-full")

        }
        this.updateFilter(this.filez, this.folders, this.filesFilter)
        return this.view
    }

    update = function() {
        this.updateFilter(this.filez, this.folders, this.filesFilter)
    }

    updateFilter = function (filez, folders, filter) {
        // Filters data according to filter and refreshes view
        let default_show = true;
        const union = filter.union | this.view != "full"
        if (union) {
            filterSet[this.view].forEach(field => {
                if (filter[field]) {
                    default_show = false;
                }
            })
        }
        for (const [filePath, value] of Object.entries(filez)) {
            let skip = false
            if (filter.pathRoot != "") {
                if (filePath.indexOf(filter.pathRoot) != 0) {
                    skip = true
                }
            }

            let show = default_show

            if (skip) {
                show = false
            } else {
                filterStraight[this.view].forEach(field => {
                    if (filter[field] !== undefined) {
                        if (union) {
                            show |= (value[field] == filter[field])
                        } else {
                            show &= (value[field] == filter[field])
                        }
                    }
                })

                if (this.view != "tiny" && ((show && !union) || (!show && union)) && filter.errors) {
                    if (!union) {
                        if (value.errors === undefined || value.errors === null || value.errors.length == 0) {
                            show = false
                        }
                    } else {
                        if (value.errors !== undefined && value.errors !== null && value.errors.length > 0) {
                            show = true
                        }
                    }
                }

                if (((show && !union) || (!show && union)) && filter.changed) {
                    if (union) {
                        show |= value.added | value.modified | value.removed | value.renamed
                    } else {
                        show &= value.added | value.modified | value.removed | value.renamed
                    }
                }

                if (show) {
                    const matchType = filter.path === undefined || filter.path === "" ? PathAny :
                        filter.path[0] == "^" ? PathStartsWidth : PathContains
                    let matchString = filePath
                    if (filter.pathRoot != "") {
                        matchString = filePath.substring(filter.pathRoot.length)
                    }
                    show &= this.pathMatch(matchType, matchString, filter.path)
                }
            }
            value.visible = show
        }
        for (const [folderPath, value] of Object.entries(folders)) {
            value.visible = false
            for (const [filePath, fileValue] of Object.entries(value.filez)) {
                if (fileValue.visible) {
                    value.visible = true
                    break
                }
            }
        }

        this.refreshView(filez, folders, filter)
    }

    updatePathFilter = function (value) {
        // Applies new path to filter
        // then filters data and refreshes view
        this.filesFilter.path = value
        this.updateFilter(this.filez, this.folders, this.filesFilter)
    }

}
