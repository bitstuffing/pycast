import socket
import ssl
import json
import re
from messenger import *

# Create a socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('0.0.0.0', 8009))
sock.listen(5)

# Wrap the socket with SSL/TLS
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('cert.pem', 'key.pem')
ssl_sock = context.wrap_socket(sock, server_side=True)

def generate_media_status(request_id):
    media_status = {
        "type": "MEDIA_STATUS",
        "status": [],
        "requestId": request_id
    }

    return json.dumps(media_status)


def generate_receiver_status(requestId=1):
    response = {
        "requestId": requestId, 
        "status": {
            "applications": [
                {
                    "appId": "CC1AD845", 
                    "displayName": "Default Media Receiver",
                    "iconUrl": "",
                    "isIdleScreen": False,
                    "launchedFromCloud": False,
                    "namespaces": [
                        {"name": "urn:x-cast:com.google.cast.cac"}, 
                        {"name": "urn:x-cast:com.google.cast.debugoverlay"}, 
                        {"name": "urn:x-cast:com.google.cast.broadcast"}, 
                        {"name": "urn:x-cast:com.google.cast.media"}
                    ], 
                    "sessionId": "854648fc-5c11-4bda-ab4b-88dec3fa8994", 
                    "statusText": "Default Media Receiver", 
                    "transportId": "854648fc-5c11-4bda-ab4b-88dec3fa8994", 
                    "universalAppId": "CC1AD845"
                }
            ], 
            "userEq": {
                "high_shelf": {"frequency": 4500.0, "gain_db": 0.0, "quality": 0.707}, 
                "low_shelf": {"frequency": 150.0, "gain_db": 0.0, "quality": 0.707}, 
                "max_peaking_eqs": 0, 
                "peaking_eqs": []
            }, 
            "volume": {
                "controlType": "master", 
                "level": 0.6000000238418579, 
                "muted": False, 
                "stepInterval": 0.019999999552965164
            }
        }, 
        "type": "RECEIVER_STATUS"
    }
    return response

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
                
                parsed_data = parse_cast_response(data)
                decoded_data = data.decode('unicode_escape')
                regex = r'(urn:[^"0-9(){}]+)'
                match = re.search(regex, decoded_data)
                namespace = None
                if match:
                    namespace = match.group(1)
                 
                if parsed_data:
                    message_type = parsed_data.get('type')
                    
                    # Respond to the message
                    if message_type == 'CONNECT':
                        print("con..")
                        response = format_message('receiver-0', 'sender-vlc', 'urn:x-cast:com.google.cast.tp.connection', json.dumps({'type': 'CONNECTED'}))
                        newsocket.send(response)
                    elif message_type == 'PING':
                        print("ping...")
                        response = format_message('receiver-0', 'sender-vlc', 'urn:x-cast:com.google.cast.tp.heartbeat', json.dumps({'type': 'PONG'}))
                        newsocket.send(response)
                    elif message_type == 'GET_STATUS':
                        if namespace == 'urn:x-cast:com.google.cast.receiver':
                            status = generate_receiver_status(parsed_data["requestId"])
                        elif namespace == 'urn:x-cast:com.google.cast.media':
                            print("2")
                            status = generate_media_status(parsed_data["requestId"])
                        else:
                            print("3")
                            print(namespace)
                            print(str(parsed_data))
                            continue  # Unknown namespace, skip this message
                        response = format_message('receiver-0', 'sender-vlc', namespace, json.dumps(status))
                        newsocket.send(response)
            else:
                break
    finally:
        # Clean up the connection
        newsocket.shutdown(socket.SHUT_RDWR)
        newsocket.close()