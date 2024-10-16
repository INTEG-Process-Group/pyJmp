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
from jmp_connection.connection_base import ConnectionBase
from jmp_connection.jmp_messages import JmpMessage, LoginMessage
from jmp_connection.socket_input_stream import SocketInputStream
# from jmp_connection.console_session import ConsoleSession

"""
Handles a JMP connection.  The JMP "JuMP" protocol is a JSON based protocol that is meant to replace the binary
JNIOR protocol.
"""


class JMPConnection(ConnectionBase):

    def __init__(self):
        """
        A socket is provided to the constructor of the JMP class.

        :param socket: only provided if we are going to treat a currently connected socket as a
        JMP connection.  This is most likely the case when implementing a server where accepted
        clients will now act as a JMP client.
        """
        ConnectionBase.__init__(self)

        self.port = 9220  # default

        self.incoming_stream = io.BytesIO()
        self.next_read_pos = 0
        self.end_of_stream_pos = 0
        self.socket_input_stream = None

        self.console_session = None

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

    """
    Authentication Methods
    """
    def is_authenticated(self):
        """
        :return: whether the connection is authenticated
        """
        return self.authenticated

    def set_credentials(self, username, password):
        self.username = username
        self.password = password
        self.attempted_credentials = False

    def wait_for_authentication(self):
        """
        sends the login and waits for the login to be processed

        :return:
        """
        self.authentication_wait_event.acquire()
        self.authentication_wait_event.wait(1000)
        self.authentication_wait_event.release()

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
                    c_thread = threading.Thread(target=self._message_received, args=[message], daemon=True)
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

    def _message_received(self, message):
        """
        Called when a message was received.
        """

        # get the json object from the message
        json_obj = json.loads(message)

        # create a MonitorMessage object
        jmp_message = JmpMessage()
        jmp_message.from_json(json_obj)

        print(f"jmp_connection: {self.get_host_info()}, recv message: {jmp_message.to_json()}")

        if "Error" == jmp_message.message:
            if "Unauthorized" in json_obj['Text']:

                if not self.attempted_credentials:
                    self.send(LoginMessage(self.username, self.password, json_obj['Nonce']))
                    self.attempted_credentials = True

                else:
                    self.on_auth(self, authorized=False, nonce=json_obj['Nonce'])

        elif "Authenticated" == jmp_message.message:
            #
            # now we are ready to use the logged in connection.  see if we have an authentication_wait_event to notify
            if self.authentication_wait_event and self.authentication_wait_event is not None:
                self.authentication_wait_event.acquire()
                self.authentication_wait_event.notify()
                self.authentication_wait_event.release()

            if not self.authenticated:
                self.authenticated = True
                # alert the on_auth handlers and let them know that the connection has
                # successfully been authenticated
                self.on_auth(self, authorized=True)

        else:
            if not self.authenticated:
                self.authenticated = True
                # alert the on_auth handlers and let them know that the connection has
                # successfully been authenticated
                self.on_auth(self, authorized=True)

            # alert the on_message handlers
            self.on_message_recv(self, jmp_message=jmp_message)

    def send(self, jmp_message) -> None:
        """
        Used to send the JNIOR message object

        :param jmp_message:
        :return: None
        """
        try:
            # get the json object as a string
            jmp_message_json_string = json.dumps(jmp_message.to_json())

            # format the message in the JMP format [length, message]
            jmp_formatted_string = f"[{len(jmp_message_json_string)},{jmp_message_json_string}]"

            if self.socket is None:
                raise Exception("socket is not open")

            # send to our connection
            self.socket.send(bytes(jmp_formatted_string, 'utf-8'))
            print(f"{str(datetime.now())[:-3]}:     sent: {jmp_message_json_string}")
        except Exception as err:
            print(f"{str(datetime.now())[:-3]}: "
                  f"unable to send {jmp_message} to {self.host}:{self.port} because {err}\n"
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
