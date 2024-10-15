import threading

from jmp_connection.jnior_listeners import JniorEvent
from jmp_connection.jnior_messages import JniorMessage


class JniorConnection:
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
        self.on_message = JniorEvent()

    def get_host_info(self):
        """
        :return: a string with information about the connection that is being used
        """
        return f"('{self.host}', {self.port})"

    """
    Event Handlers
    """
    def add_connection_handler(self, connection_event_handler):
        """
        adds a given message event handler to the on_connection JniorEvent object
        """
        self.on_connection += connection_event_handler

    def remove_connection_handler(self, connection_event_handler):
        """
        removes a given message event handler to the on_connection JniorEvent object
        """
        self.on_connection -= connection_event_handler

    def add_auth_handler(self, auth_event_handler):
        """
        adds a given message event handler to the on_auth JniorEvent object
        """
        self.on_auth += auth_event_handler

    def remove_auth_handler(self, auth_event_handler):
        """
        removes a given message event handler to the on_auth JniorEvent object
        """
        self.on_auth -= auth_event_handler

    def add_message_handler(self, message_event_handler):
        """
        adds a given message event handler to the on_message JniorEvent object
        """
        self.on_message += message_event_handler

    def remove_message_handler(self, message_event_handler):
        """
        removed a given message event handler to the on_message JniorEvent object
        """
        self.on_message -= message_event_handler

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
        self.send(JniorMessage())
