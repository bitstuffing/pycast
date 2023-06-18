import socket
import ssl
import json
from messenger import *

# Create a socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('0.0.0.0', 8009))
sock.listen(5)

# Wrap the socket with SSL/TLS
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('cert.pem', 'key.pem')
ssl_sock = context.wrap_socket(sock, server_side=True)

while True:
    # Accept a connection
    newsocket, fromaddr = ssl_sock.accept()
    try:
        print('Accepted connection from', fromaddr)
        
        # Receive data and print it out
        while True:
            data = newsocket.recv(1024)
            if data:
                print('Received:', data)
                
                # Parse the received data
                parsed_data = parse_cast_response(data)
                if parsed_data:
                    message_type = parsed_data.get('type')
                    
                    # Respond to the message
                    if message_type == 'CONNECT':
                        response = format_message('receiver-0', 'sender-vlc', 'urn:x-cast:com.google.cast.tp.connection', json.dumps({'type': 'CONNECTED'}))
                        newsocket.send(response)
                    elif message_type == 'PING':
                        response = format_message('receiver-0', 'sender-vlc', 'urn:x-cast:com.google.cast.tp.heartbeat', json.dumps({'type': 'PONG'}))
                        newsocket.send(response)
                    elif message_type == 'GET_STATUS':
                        status = {'type': 'STATUS', 'status': {}}
                        response = format_message('receiver-0', 'sender-vlc', 'urn:x-cast:com.google.cast.receiver', json.dumps(status))
                        newsocket.send(response)
            else:
                break
    finally:
        # Clean up the connection
        newsocket.shutdown(socket.SHUT_RDWR)
        newsocket.close()
