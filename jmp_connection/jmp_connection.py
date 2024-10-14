import logging
from datetime import datetime

import io
import json
import socket
import ssl
import threading
import time
import traceback

from jmp_connection.data_input_stream import DataInputStream
from jmp_connection.jnior_connection import JniorConnection
from jmp_connection.socket_input_stream import SocketInputStream
# from jmp_connection.console_session import ConsoleSession

"""
Handles a JMP connection
"""


class JMPConnection(JniorConnection):

    def __init__(self):
        """
        A socket is provided to the constructor of the JMP class.

        :param socket: only provided if we are going to treat a currently connected socket as a
        JMP connection.  This is most likely the case when implementing a server where accepted
        clients will now act as a JMP client.
        """
        JniorConnection.__init__(self)

        self.port = 9220  # default

        self.incoming_stream = io.BytesIO()
        self.next_read_pos = 0
        self.end_of_stream_pos = 0
        self.socket_input_stream = None

        self.console_session = None

    """
    Get and set methods for the socket
    """
    def set_socket(self, socket):
        if socket is None:
            raise Exception("Socket is None")
        if self.socket is not None:
            raise Exception("Socket is already defined")
        self.socket = socket
        self.host, self.port = self.socket.getpeername()
        self.connected()

    def get_socket(self):
        return self.socket

    """
    Connection Methods
    """
    def connect(self, host=None, port=None):
        """ connect ([host[, port]])

        Called to connect to a JMP server.  if a host is not provided then the saved host will be
        used

        :param host: optional to specify a new client host
        :param port: optional to specify a port other than the default 9220
        """

        if host is not None:
            self.host = host
            if port is not None:
                self.port = port

        try:
            if self.host is None:
                raise Exception("host is not defined")

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))

            self.connected()

            return True
        except Exception as err:
            print(f"{str(datetime.now())[:-3]}: unable to connect to {self.host}:{self.port} "
                  f"because {err}\n{traceback.format_exc()}")
            # close and nullify our socket
            self.socket.close()
            self.socket = None

            return False

    def start_tls(self):
        """
        start_tls

        called to upgrade the connection to a secure connection
        """

        print(f"{str(datetime.now())[:-3]}: upgrading socket to TLS")
        tls_start_time = time.time()

        # tell the JNIOR that we wish to upgrade to TLS.  Must sleep briefly before performing
        # the upgrade
        self.socket.send(b'[STARTTLS]')
        time.sleep(.2)

        # create a ssl socket to use and tell it to perform the handshake before continuing
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_socket = context.wrap_socket(self.socket)

        # reassign our socket
        self.socket = ssl_socket

        tls_elapsed = time.time() - tls_start_time
        print(f"{str(datetime.now())[:-3]}: upgrading socket to TLS took {tls_elapsed}")

    def close(self):
        """
        closes and nullifies the socket
        """
        self.socket_input_stream.close()
        if self.socket is not None:
            self.socket.close()
            self.socket = None

            # alert listener handlers that the connection has been closed
            self.on_connection(self, connected=False, socket=self.socket)

    def is_connected(self):
        """
        :return: whether the connection is connected
        """
        return self.socket is not None

    def _message_receive_loop(self):
        """
        private method used to monitor the socket for incoming messages
        """

        self.socket_input_stream = SocketInputStream(self.socket)

        # define our data input stream.  this makes reading the input stream nicer
        data_input_stream = DataInputStream(self.socket_input_stream)

        while True:
            try:
                self.socket_input_stream.read_available()

                # now try to process as many messages as there are in our stream
                while self.socket_input_stream.data_available():
                    # # seek to our next read position
                    # self.incoming_stream.seek(self.next_read_pos)

                    # do we have an opening '['
                    left_bracket = data_input_stream.read_char()
                    if left_bracket != '[':
                        #
                        # we dont need to throw an exception here.  we should just ignore this byte and try the next one
                        # raise Exception('left bracket expected')
                        continue

                    length_string = ""
                    while True:
                        next_char = data_input_stream.read_char()
                        if '0' <= next_char <= '9':
                            length_string = length_string + next_char
                        else:
                            break
                    length = int(length_string)

                    # next char should be a comma
                    if ',' != next_char:
                        raise Exception("comma expected")

                    self.next_read_pos = self.incoming_stream.tell()

                    # read the data based on the received length
                    message_bytes = data_input_stream.read_bytes(length)

                    right_bracket = data_input_stream.read_char()
                    if right_bracket != ']':
                        raise Exception('right bracket expected')

                    message = str(message_bytes, 'ascii')

                    # kick a new thread to handle the received message
                    c_thread = threading.Thread(target=self.message_received, args=[message], daemon=True)
                    c_thread.start()

            except Exception as err:

                # if the socket has already been nullified then it was gracefully closed
                if self.socket_input_stream.is_closed():
                    break

                logging.error(f"error while reading from {self.host}:{self.port} because {err}\n"
                              f"{traceback.format_exc()}")
                self.close()
                # alert listener handlers that we have lost our connection
                self.on_connection(self, connected=False)

    def send(self, jnior_message) -> None:
        """
        Used to send the JNIOR message object

        :param jnior_message:
        :return: None
        """
        try:
            # get the json object as a string
            jnior_message_json_string = json.dumps(jnior_message.to_json())

            # format the message in the JMP format [length, message]
            jmp_formatted_string = f"[{len(jnior_message_json_string)},{jnior_message_json_string}]"

            if self.socket is None:
                raise Exception("socket is not open")

            # send to our connection
            self.socket.send(bytes(jmp_formatted_string, 'utf-8'))
            print(f"{str(datetime.now())[:-3]}:     sent: {jnior_message_json_string}")
        except Exception as err:
            print(f"{str(datetime.now())[:-3]}: "
                  f"unable to send {jnior_message} to {self.host}:{self.port} because {err}\n"
                  f"{traceback.format_exc()}")
            # close and nullify our socket
            self.close()
            # alert listener handlers that we have lost our connection
            self.on_connection(self, connected=False)

    def get_console_session(self):
        """
        :return: a console session.  if one has not yet been established then one will be created now
        """
        if self.console_session is None:
            console_session = ConsoleSession(self)
            self.console_session = console_session if console_session.open() else None
        return self.console_session
