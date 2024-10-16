import copy
import hashlib
import json
import uuid


class JmpMessage(object):
    EMPTY = {}

    def __init__(self, message=None):
        if message is None:
            message = ""

        self.json = {
            "Message": message,
            "Meta": {"Hash": str(uuid.uuid4())[:8]}
        }

    def dup(self, jmp_message):
        """
        used internally to duplicate the given jmp_message object
        :param jmp_message:
        :return:
        """
        if jmp_message is not None:
            self.json = copy.copy(jmp_message.json)

    @property
    def message(self):
        return self.json["Message"]

    @property
    def meta(self):
        return self.json["Meta"] if "Meta" in self.json else None

    def from_json(self, json):
        self.json = json

    def to_json(self):
        return self.json


class LoginMessage(JmpMessage):
    def __init__(self, username, password, nonce):
        JmpMessage.__init__(self)

        md5_hash = hashlib.md5(bytes(f"{username}:{nonce}:{password}", 'utf'))
        digest = str(md5_hash.hexdigest())
        digest = username + ":" + digest

        self.json["Auth-Digest"] = digest

    @property
    def auth_digest(self):
        return self.json["Auth-Digest"]


class MonitorMessage(JmpMessage):
    def __init__(self):
        JmpMessage.__init__(self)

    @property
    def model(self):
        return self.json["Model"]

    @property
    def serial_number(self):
        return self.json["Serial Number"]

    @property
    def version(self):
        return self.json["Version"]

    @property
    def inputs(self):
        return self.json["Inputs"]

    @property
    def outputs(self):
        return self.json["Outputs"]

    @property
    def timestamp(self):
        return self.json["Timestamp"]


class ControlOutputMessage(JmpMessage):
    def __init__(self, command, channel):
        JmpMessage.__init__(self, "Control")
        self.json["Command"] = command
        self.json["Channel"] = channel


class CloseMessage(ControlOutputMessage):
    def __init__(self, channel, duration=None):
        ControlOutputMessage.__init__(self, "Close", channel)
        if duration is not None:
            self.json["Duration"] = duration


class FileListMessage(JmpMessage):
    def __init__(self, folder="/"):
        JmpMessage.__init__(self, "File List")
        self.json["Folder"] = folder


class FileListResponseMessage(JmpMessage):
    def __init__(self):
        JmpMessage.__init__(self)

    @property
    def folder(self):
        if not self.json["Folder"].endswith('/'):
            self.json["Folder"] = self.json["Folder"] + '/'
        return self.json["Folder"]

    @property
    def bytes_free(self):
        return self.json["BytesFree"]

    @property
    def contents(self):
        return self.json["Content"]


class FileReadMessage(JmpMessage):
    def __init__(self, filename, offset=None, limit=1024*16):
        JmpMessage.__init__(self, "File Read")

        if not filename.startswith("/"):
            filename = f"/{filename}"
        self.json["File"] = filename
        self.json["Limit"] = limit
        if None is not offset:
            self.json["Offset"] = offset


class FileReadResponseMessage(JmpMessage):
    def __init__(self):
        JmpMessage.__init__(self)

    @property
    def file(self):
        return self.json["File"]

    @property
    def status(self):
        return self.json["Status"]

    @property
    def data(self):
        return self.json["Data"] if "Succeed" == self.status else None

    @data.setter
    def data(self, value):
        self.json["Data"] = value

    @property
    def size(self):
        return int(self.json["Size"])

    @size.setter
    def size(self, value):
        self.json["Size"] = value

    @property
    def limit(self):
        return self.json["Limit"] if "Limit" in self.json else None

    @property
    def num_read(self):
        return self.json["NumRead"] if "NumRead" in self.json else None

    @property
    def offset(self):
        return self.json["Offset"] if "Offset" in self.json else None


class RegistryReadMessage(JmpMessage):
    def __init__(self, keys=[]):
        JmpMessage.__init__(self, "Registry Read")
        self.json["Keys"] = keys


class RegistryResponseMessage(JmpMessage):
    def __init__(self):
        JmpMessage.__init__(self)

    @property
    def keys(self):
        return self.json["Keys"]


class PostMessage(JmpMessage):
    def __init__(self, number, content_json):
        JmpMessage.__init__(self, "Post Message")
        self.json["Number"] = number
        self.json["Content"] = json.dumps(content_json)
