import threading
import traceback
from datetime import datetime
import socket

from jmp_connection.jnior_event import JniorEvent
from jmp_connection.jmp_messages import JmpMessage


class ConnectionBase:
    def __init__(self):
        """
        A base class for JNIOR connections.  This can be overriden by class implementations like a
         websocket implementation or jmp implementation
        """

        self.socket = None
        self.host = None

        # we set this to zero because it should be overridden with the correct default port by the
        # overriding class
        self.port = 0

        self.username = None
        self.password = None
        self.attempted_credentials = False

        self.authentication_wait_event = threading.Condition()
        self.authenticated = False

        # Jnior Events
        self.on_connection = JniorEvent()
        self.on_auth = JniorEvent()
        self.on_message_recv = JniorEvent()

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
            if self.socket is not None:
                self.socket.close()
                self.socket = None

            return False

    def get_host_info(self):
        """
        :return: a string with information about the connection that is being used
        """
        return f"('{self.host}', {self.port})"

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

    """
    Event Handlers
    """
    def add_connection_handler(self, connection_event_handler):
        """
        adds a given event handler to the on_connection JniorEvent object
        """
        self.on_connection += connection_event_handler

    def remove_connection_handler(self, connection_event_handler):
        """
        removes a given event handler to the on_connection JniorEvent object
        """
        self.on_connection -= connection_event_handler

    def add_auth_handler(self, auth_event_handler):
        """
        adds a given event handler to the on_auth JniorEvent object
        """
        self.on_auth += auth_event_handler

    def remove_auth_handler(self, auth_event_handler):
        """
        removes a given event handler to the on_auth JniorEvent object
        """
        self.on_auth -= auth_event_handler

    def add_message_recv_handler(self, message_event_handler):
        """
        adds a given event handler to the on_message JniorEvent object
        """
        self.on_message_recv += message_event_handler

    def remove_message_recv_handler(self, message_event_handler):
        """
        removed a given event handler to the on_message JniorEvent object
        """
        self.on_message_recv -= message_event_handler

    def connected(self):
        """
        Called when we are either given a currently established socket or after a new socket
        that we create has been successfully connected.
        """
        # alert listener handlers that we have a valid connection
        self.on_connection(self, connected=True, socket=self.socket)

        # start a new thread to handle incoming messages
        c_thread = threading.Thread(target=self._message_receive_loop, args=(), daemon=True)
        c_thread.start()

        # send an empty message so that we get an error - unauthenticated response with a
        # Nonce to use in our login message
        self.send(JmpMessage())
