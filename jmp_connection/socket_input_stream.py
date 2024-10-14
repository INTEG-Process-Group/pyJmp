import io


class SocketInputStream(object):
    def __init__(self, socket):
        self.socket = socket
        self.incoming_stream = io.BytesIO()
        self.next_read_pos = 0
        self.end_of_stream_pos = 0
        self.closed = False

    def data_available(self):
        return self.incoming_stream.tell() < self.end_of_stream_pos

    def read_available(self):
        self._read()

    def read(self, count):
        while self.incoming_stream.tell() + count > self.end_of_stream_pos:
            self._read()

        return self.incoming_stream.read(count)

    def _read(self):
        data = self.socket.recv(1024)

        if 0 < len(data):
            # capture where is the stream we are currently reading from
            self.next_read_pos = self.incoming_stream.tell()

            # we have read all that has been received.  we can reset our pointers
            if self.next_read_pos == self.end_of_stream_pos:
                self.next_read_pos = 0
                self.end_of_stream_pos = 0
                self.incoming_stream.truncate(0)

            # seek to the end of the stream and write the data that was just read
            self.incoming_stream.seek(self.end_of_stream_pos)
            self.incoming_stream.write(data)

            # capture the new end of the stream
            self.end_of_stream_pos = self.incoming_stream.tell()

            # seek back to the position where we were last reading from
            self.incoming_stream.seek(self.next_read_pos)

    def close(self):
        self.closed = True

    def is_closed(self):
        return self.closed

    def tell(self):
        return self.incoming_stream.tell()

    def seek(self, offset, whence=0):
        self.incoming_stream.seek(offset, whence)
