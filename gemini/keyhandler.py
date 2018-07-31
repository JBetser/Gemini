import warnings

class KeyData(object):
    def __init__(self, secret):
        self.secret = secret

class KeyHandler(object):
    def __init__(self, filename=None):
        self._keys = {}
        self.resaveOnDeletion = False
        self.filename = filename
        if filename is not None:
            with open(filename, "r") as f:
                while True:
                    key = f.readline().strip()
                    if not key:
                        break
                    secret = f.readline().strip()
                    self.addKey(key, secret)

    def __del__(self):
        self.close()

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def keys(self):
        return self._keys.keys()

    def getKeys(self):
        return self._keys.keys()

    def addKey(self, key, secret):
        self._keys[key] = KeyData(secret)

    def getSecret(self, key):
        data = self._keys.get(key)
        if data is None:
            raise Exception("Key not found: %r" % key)

        return data.secret
