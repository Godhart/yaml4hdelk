# FileData:

```js
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
```

# LocalData:

## Members

```js
    session = null      // Current session timestamp. Used to understand if session is outdated
                        // (detect if another session were opened on other browser tab)
    filesData = {}      // Dict with file data. Key is file path, value is FileData instance
    activeTabs = []     // List of active tabs, that should be displayed in editor. Value is file path
    currentTab = ""     // Currently selected tab. Value is file path
    dataDomain = ""     // Current data domain
    co = {}             // Named Constants for current data domain
    ifCreated = null    // Promise, resolved when Object creation is complete
    remoteData = null   // Object to access remote data (file lists and metadata)
    remoteFiles = null  // Object to load / save files to remote
```

## External interface

### General Storage related

[x] switchDomain                                                // Load local data for specified data domain. Flush current data if necessary
[x] newSession                                                  // Register new session (data domain specific)
[x] releaseSession                                              // Release current session
[T] reload                                                      // Reload data from local storage
                                                                // # TODO: also remove obsolete data and mark outdated files
[x] storeAll                                                    // Flush all current data into local storage
[t] exportData                                                  // Export all data to the dict in the unified format
# TODO: cleanup unnecessary data

### General File related
[m] ensureFileData(filePath, wantContent)                       // Ensure there is local meta and/or content for specified filePath, checkout if necessary
[m] dropFile(filePath)                                          // Drops any changes and local marks, removes file record from internal database
[m] currentValue(filePath)                                      // Returns current value for specified path
[m] setCurrentValue(filePath, value)                            // Sets current value for specified filePath
[-] addFile(filePath)                                           // Adds a new file
[-] removeFile(filePath)                                        // Remove a file (mark file as pending for remove, don't touch anything else)
# TODO: ? get current meta for specified filePath ?

### Tabs related
[m] addTab(filePath)                                            // Add tab (into list of tabs)
[m] removeTab(filePath)                                         // Removes tab from list
[m] switchTab(filePath)                                         // Changes current tab to specified filePath

### Massive value/meta update
[m] updateFilesAndTabs(data)                                    // Updates current values and tabs list
[m] updateProblemsEditor(data)                                  // Updates info with problems detected by editor
[m] updateProblemsRemote(data)                                  // Updates info with problems detected by remote

### Per file
[m] toggleFav(filePath)                                         // Toggles FAV mark for specified path

## Internal interface

[m] updateMetaFromRemote(filePath)                              // Updates file metadata from remoteData
[m] updateSourceFromRemote(filePath)                            // Updates file content from remoteFiles
[m] checkoutFileData(filePath, source, hash, timestamp)         // Makes file checkout with provided values
[m] updateCheckoutFileData(filePath, source, hash, timestamp)   // Updates checkout (not current) data with new values
[m] removeObsolete
[m] checkOutdate
