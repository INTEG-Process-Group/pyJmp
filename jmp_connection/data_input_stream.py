"""
Reading from Java DataInputStream format.
"""
import io
import struct


class DataInputStream:
    def __init__(self, stream):
        self.stream = stream

        cur_pos = self.stream.tell()
        stream.seek(0, io.SEEK_END)
        self.length = stream.tell()
        stream.seek(cur_pos)

    def read_boolean(self):
        return struct.unpack('?', self.stream.read(1))[0]

    def read_byte(self):
        return struct.unpack('b', self.stream.read(1))[0]

    def read_unsigned_byte(self):
        return struct.unpack('B', self.stream.read(1))[0]

    def read_char(self):
        return chr(struct.unpack('b', self.stream.read(1))[0])

    def read_double(self):
        return struct.unpack('>d', self.stream.read(8))[0]

    def read_float(self):
        return struct.unpack('>f', self.stream.read(4))[0]

    def read_short(self):
        return struct.unpack('>h', self.stream.read(2))[0]

    def read_unsigned_short(self):
        return struct.unpack('>H', self.stream.read(2))[0]

    def read_int(self):
        return struct.unpack('>i', self.stream.read(4))[0]

    def read_unsigned_int(self):
        return struct.unpack('>I', self.stream.read(4))[0]

    def read_long(self):
        return struct.unpack('>q', self.stream.read(8))[0]

    def read_unsigned_long(self):
        return struct.unpack('>Q', self.stream.read(8))[0]

    def read_string(self):
        utf_length = struct.unpack('>B', self.stream.read(1))[0]
        return str(self.stream.read(utf_length), 'ascii')

    def read_string(self):
        utf_length = struct.unpack('>B', self.stream.read(1))[0]
        return str(self.stream.read(utf_length), 'ascii')

    def read_string2(self):
        utf_length = self.read_short()
        return str(self.stream.read(utf_length), 'ascii')

    def read_utf(self):
        utf_length = struct.unpack('>H', self.stream.read(2))[0]
        return str(self.stream.read(utf_length), 'utf')

    def read_bytes(self, length):
        return self.stream.read(length)

    def read_remaining(self):
        return self.stream.read()

    def get_remaining_length(self):
        return self.length - self.stream.tell()
