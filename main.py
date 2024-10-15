import time

from jmp_connection.jmp_connection import JMPConnection
from jmp_connection.jnior_messages import LoginMessage, CloseMessage


def connection_handler(jmp_connection2, connected, socket):
    """
    called when the connection is either connected or disconnected

    :param jmp_connection2:
    :param connected:
    :param socket:
    :return:
    """
    print(f"jmp_connection: {jmp_connection2}, {socket} is connected: {connected}")


def auth_handler(jmp_connection2, authorized, nonce=None):
    """
    called when we either receive an authenticated or unauthenticated message.  If credentials have been provided then
    they will be tried before calling this method.

    :param jmp_connection2:
    :param authorized:
    :param nonce:
    :return:
    """
    print(f"jmp_connection: {jmp_connection2}, authorized: {authorized}, nonce: {nonce}")

    if not authorized:
        jmp_connection2.send(LoginMessage("jnior", "jnior", nonce))

    if authorized:
        #
        # we are now ready to use the connection
        pass


def message_handler(jmp_connection2, jnior_message):
    """
    called when the jmp connection receives a message

    :param jmp_connection2:
    :param jnior_message:
    :return:
    """
    print(f"jmp_connection: {jmp_connection2}, recv message: {jnior_message.to_json()}")


jmp_connection = JMPConnection()
jmp_connection.set_credentials("jnior", "jnior")
jmp_connection.add_connection_handler(connection_handler)
# jmp_connection.add_auth_handler(auth_handler)
jmp_connection.add_message_handler(message_handler)
jmp_connection.connect("10.0.0.78", 9220)

#
# at this point in the code we are connected but we arent actually ready to use the connection.  the connect
# call above does not block for the authentication to be successful.  That gets done asynchronously.
print(f"is authenticated: {jmp_connection.is_authenticated()}")

jmp_connection.wait_for_authentication()

#
# we should now be authenticated since we used the wait event.  lets print the authentication state to be sure
print(f"is authenticated: {jmp_connection.is_authenticated()}")

#
# we are ready to use the connection now

#
# try to close pulse as a test
jmp_connection.send(CloseMessage(1, 1000))

time.sleep(5)

jmp_connection.close()

print('done')
