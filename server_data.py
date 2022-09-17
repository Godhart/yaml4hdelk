import os
import hashlib


def new_domain(name, path, meta_path=None):
    """
    Factory for new domain object
    Selects domain which fits for selected path
    """
    for cl in (DataDomain, ):
        if cl.path_supported(path):
            return cl(name, path, meta_path)
    return None


_CONTENT = "content"
_HASH = "hash"
_LOCK = "lock"
_TIMESTAMP = "timestamp"


class DataDomain:
    """
    DataDomain provides ways for data storage abstraction
    """
    # TODO: check where custom_data is missing

    def __init__(self, name, path, meta_path=None):
        self._name = name
        self._path = path               # Path to data files
        if meta_path is None:
            meta_path = path
        self._meta_path = meta_path     # Path to metadata for files
        # TODO: check that path exist

    @staticmethod
    def path_supported(path):
        if path[0] == "/" or path[0] == ".":
            return True
        return False

    @staticmethod
    def _lock_hash(secret):
        return hashlib.md5(str(secret).encode()).hexdigest()

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def meta_path(self):
        return self._meta_path

    def _full_path(self, file_path):
        # NOTE: depends on domain kind
        return os.path.join(self.path, file_path)

    def _aux_path(self, file_path):
        return os.path.join(self.meta_path, file_path)

    def _file_exists(self, file_path, custom_data=None):
        # NOTE: depends on domain kind
        if custom_data is not None:
            # TODO: support custom data
            raise NotImplementedError("custom data is not supported yet")
        return os.path.isfile(self._full_path(file_path))

    def _find_file(self, from_path, path_pattern, custom_data=None):
        raise NotImplementedError("DataDomain._find_file Not implemented yet")
        if custom_data is not None:
            # TODO: support custom data
            raise NotImplementedError("custom data is not supported yet")
        return None

    def _file_binary(self, file_path, custom_data=None):
        # NOTE: depends on domain kind
        if custom_data is not None:
            # TODO: support custom data
            raise NotImplementedError("custom data is not supported yet")
        with open(self._full_path(file_path), "rb") as f:
            return f.read()

    def _file_text(self, file_path, custom_data=None):
        # NOTE: depends on domain kind
        if custom_data is not None:
            # TODO: support custom data
            raise NotImplementedError("custom data is not supported yet")
        with open(self._full_path(file_path), "r") as f:
            return f.read()

    def _file_hash(self, file_path, custom_data=None):
        return hashlib.md5(self._file_binary(file_path, custom_data)).hexdigest()

    def _file_timestamp(self, file_path, custom_data=None):
        # NOTE: depends on domain kind
        if custom_data is not None:
            # TODO: support custom data
            raise NotImplementedError("custom data is not supported yet")
        # TODO: special case for custom_data (first look in custom data)
        if self._file_exists(file_path, None):
            return int(os.path.getmtime(self._full_path(file_path)))
        else:
            return 0

    def _file_lock(self, file_path, custom_data=None):
        # NOTE: depends on domain kind (also could be http, git)
        # NOTE: http files are always locked
        if not self._file_exists(file_path, custom_data):
            return None
        else:
            lock_path = self._aux_path(file_path+".lock")
            if os.path.isfile(lock_path):
                with open(lock_path, "r") as f:
                    return f.readline().strip()
            else:
                return ""

    def _file_lock_set(self, file_path, lock):
        # NOTE: depends on domain kind (also could be http, git)
        # NOTE: http files are always locked
        lock_path = self._aux_path(file_path+".lock")
        if lock is not None:
            with open(lock_path, "w") as f:
                f.write(lock)
        else:
            if os.path.isfile(lock_path):
                os.remove(lock_path)

    def list_files(self, custom_data=None):
        # NOTE: depends on domain kind (also could be http, git)
        if custom_data is not None:
            # TODO: support custom data
            raise NotImplementedError("custom data is not supported yet")
        root_path = self.path
        result = []
        offs = len(root_path)
        for root, dirs, files in os.walk(root_path):
            result += [os.path.join(root[offs:], f)
                       for f in files if f[-4:].lower() == ".yml" or f[-5:].lower() == ".yaml"]
            if offs == len(root_path):
                offs += 1

        sorted(result, key=lambda x: str(x.count(os.path.sep)) + x)
        return sorted(result)

    def get_files_hash(self, files, custom_data=None):
        """ Return hashes (as dict) for specified files within domain """

        if files is None:
            files = self.list_files(custom_data)

        hashes = {}
        for file_path in files:
            hashes[file_path] = self._file_hash(file_path, custom_data)

        return hashes

    def get_files_lock(self, files, custom_data=None):
        """ Return lock info (as dict) for specified files within domain """
        if files is None:
            files = self.list_files(custom_data)

        locks = {}
        for file_path in files:
            lock = self._file_lock(file_path, custom_data)
            if lock != "":  # NOTE: unlocked files are skipped in result
                locks[file_path] = lock

        return locks

    def lock(self, file_path, force, secret, dry_run, custom_data=None):
        """
        Locks files from changes by anyone without secret
        Returns lock value (secret's hash) in case of success
        """
        lock = self._lock_hash(secret)

        if file_path == "test":
            return lock, None

        current_lock = self._file_lock(file_path, custom_data)
        if current_lock is None:
            return None, f"File '{file_path}' is not found in domain '{self.name}'"

        if not force and current_lock != "":
            return None, f"File '{file_path}' in domain '{self.name}' is already locked"

        if not dry_run:
            try:
                self._file_lock_set(file_path, lock)
            except Exception as e:
                return None, f"Failed to set lock on '{file_path}' in domain '{self.name}' due to exception: {e}! "

        return lock, None

    def unlock(self, file_path, secret, force, custom_data=None):
        """
        Unlocks file, so anyone could change it
        Necessary secret is required to unlock file
        Returns True in case of success
        """
        if secret is None:
            return None, f"No secret were provided!"

        lock = self._lock_hash(secret)

        current_lock = self._file_lock(file_path, custom_data)
        if current_lock is None:
            return None, f"File '{file_path}' is not found in domain '{self.name}'"

        if current_lock == "":
            return True, None

        if not force and lock != current_lock:
            return None, f"Secret for '{file_path}' in domain '{self.name}' is wrong!"

        try:
            self._file_lock_set(file_path, None)
        except Exception as e:
            return None, f"Failed to unlock '{file_path}' in domain '{self.name}' due to exception: {e}!"

        return True, None

    def get_file(self, file_path, fields, custom_data=None):
        if not self._file_exists(file_path, custom_data):
            file_exists = False
        else:
            file_exists = True

        result = {}

        if _CONTENT in fields:
            if not file_exists:
                result[_CONTENT] = None
            else:
                try:
                    result[_CONTENT] = self._file_text(file_path, custom_data)
                except Exception as e:
                    return None, f"File read '{file_path}' of domain '{self.name}' failed due to exception: {e}"

        if _HASH in fields:
            if not file_exists:
                result[_HASH] = None
            else:
                try:
                    result[_HASH] = self._file_hash(file_path, custom_data)
                except Exception as e:
                    return None, f"Getting file hash for file '{file_path}' of domain '{self.name}' failed due to exception: {e}"

        if _LOCK in fields:
            try:
                lock = self._file_lock(file_path, custom_data)
                if lock is not None and lock != "":
                    result[_LOCK] = lock
            except Exception as e:
                return None, f"Getting file lock for file '{file_path}' of domain '{self.name}' failed due to exception: {e}"

        if _TIMESTAMP in fields:
            if not file_exists:
                result[_TIMESTAMP] = None
            else:
                try:
                    result[_TIMESTAMP] = self._file_timestamp(
                        file_path, custom_data)
                except Exception as e:
                    return None, f"Getting file timestamp for file '{file_path}' of domain '{self.name}' failed due to exception: {e}"

        return result, None

    def save_file(self, file_path, content):
        # NOTE: depends on domain kind
        # NOTE: locks shouldn't be checked since DataDomain only provides ways for data storage abstraction
        try:
            with open(self._full_path(file_path), "w") as f:
                f.write(content)
        except Exception as e:
            return None, f"Failed to save file '{file_path}' in domain '{self.name}' due to exception: {e}!"

        return True, None
