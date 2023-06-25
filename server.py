import OpenSSL
import socket
import signal
import sys

from messenger import *

import logging
logging.basicConfig(level=logging.DEBUG)

conn = None
sock = None

def signal_handler(signal, frame):
    print('Ctrl+C pressed! Closing the socket.')
    try:
        if conn:
            conn.shutdown()
        if sock:
            sock.close()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('0.0.0.0', 8009))
sock.listen(5)

context = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
context.use_certificate_file('cert.pem')
context.use_privatekey_file('key.pem')

while True:
    client_sock, fromaddr = sock.accept()
    conn = OpenSSL.SSL.Connection(context, client_sock)
    conn.set_accept_state()
    accepted = False
    try:
        conn.do_handshake()
        accepted = True
        print('Connection accepted from', fromaddr)
    except OpenSSL.SSL.Error as e:
        print(f"Handshake failed: {e}")
        continue

    if accepted:
        try:
            while True:
                try:
                    data = conn.recv(1024)
                except OpenSSL.SSL.Error as e:
                    print(f"SSL error occurred: {e}")
                    break
                except Exception as e:
                    print(f"Unexpected error occurred: {e}")
                    break

                if data:
                    print('Received:', data)
                    handle_received_data(data, conn)
                else:
                    break
        finally:
            conn.shutdown()
