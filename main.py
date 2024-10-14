import time

from jmp_connection.jmp_connection import JMPConnection
from jmp_connection.jnior_messages import LoginMessage


def connection_handler(jmp_connection2, connected, socket):
    print(f"jmp_connection: {jmp_connection2}, {socket} is connected: {connected}")


def auth_handler(jmp_connection2, authorized, nonce=None):
    print(f"jmp_connection: {jmp_connection2}, authorized: {authorized}, nonce: {nonce}")

    if not authorized:
        jmp_connection2.send(LoginMessage("jnior", "jnior", nonce))

    if authorized:
        #
        # now we are ready to use the logged in connection
        pass


def message_handler(jmp_connection2, jnior_message):
    print(f"jmp_connection: {jmp_connection2}, recv message: {jnior_message.to_json()}")


jmp_connection = JMPConnection()
jmp_connection.add_connection_handler(connection_handler)
jmp_connection.add_auth_handler(auth_handler)
jmp_connection.add_message_handler(message_handler)
jmp_connection.connect("10.0.0.65", 9220)

time.sleep(5)

jmp_connection.close()

print('done')
