import time

from jmp_connection.jmp_connection import JMPConnection
from jmp_connection.jmp_messages import LoginMessage, CloseMessage, PostMessage


def connection_handler(jmp_connection2, connected, socket):
    """
    called when the connection is either connected or disconnected

    :param jmp_connection2:
    :param connected:
    :param socket:
    :return:
    """
    if connected:
        print(f"{jmp_connection2}: is now connected to {socket}")
    else:
        print(f"{jmp_connection2}: has disconnected")


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


def message_handler(jmp_connection2, jmp_message):
    """
    called when the jmp connection receives a message

    :param jmp_connection2:
    :param jmp_message:
    :return:
    """
    print(f"jmp_connection: {jmp_connection2.get_host_info()}, recv message: {jmp_message.to_json()}")


#
# define the JMP connection object
jmp_connection = JMPConnection()

#
# these handlers are optional and only specified for example purposes
jmp_connection.add_connection_handler(connection_handler)
jmp_connection.add_auth_handler(auth_handler)
jmp_connection.add_message_handler(message_handler)

#
# set the credentials to use.  if they fail then the auth_handler, if one is defined, would be called.
jmp_connection.set_credentials("jnior", "jnior2")

#
# connect to the JMP server
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

#
# try sending a macro execution request
jmp_connection.send(PostMessage(2000, {"Message": "macro.execute", "MacroName": "open_shutter"}))

time.sleep(5)

jmp_connection.close()

print('done')
