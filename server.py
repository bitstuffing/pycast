import socket
import ssl
import json
import re
from messenger import *
import uuid

import subprocess

# Create a socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('0.0.0.0', 8009))
sock.listen(5)

# Wrap the socket with SSL/TLS
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('cert.pem', 'key.pem')
ssl_sock = context.wrap_socket(sock, server_side=True)

def generate_media_status(requestId=0, contentId="https://telemadridhls2-live-hls.secure2.footprint.net/egress/chandler/telemadrid/telemadrid_1/index.m3u8"):
    response = {
        "requestId": requestId, 
        "status": [{
            "mediaSessionId": 1, 
            "playbackRate": 1, 
            "playerState": "IDLE", 
            "currentTime": 0, 
            "supportedMediaCommands": 12303,#274447, 
            "volume": {
                "level": 1, 
                "muted": False
            }, 
            "media": {
                "contentId": contentId, 
                "streamType": "BUFFERED", 
                "contentType": "application/x-mpegURL", 
                "metadata": {}
            }, 
            "currentItemId": 1, 
            "extendedStatus": {
                "playerState": "LOADING", 
                "media": {
                    "contentId": contentId, 
                    "streamType": "BUFFERED", 
                    "contentType": "application/x-mpegURL", 
                    "metadata": {}
                }, 
                "mediaSessionId": 1
            }, 
            "repeatMode": "REPEAT_OFF"
        }], 
        "type": "MEDIA_STATUS"
    }
    
    return response


def generate_receiver_status(requestId=1):
    response = {
        "requestId": requestId, 
        "status": {
            "applications": [{
                "appId": "CC1AD845",
                "appType": "WEB",
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
                "sessionId": session_id,
                "statusText": "Default Media Receiver",
                "transportId": transport_id,
                "universalAppId": "CC1AD845"
            }],
            "userEq": {}, 
            "volume": {
                "controlType": "attenuation", 
                "level": 1.0, 
                "muted": False, 
                "stepInterval": 0.05000000074505806
            }
        }, 
        "type": "RECEIVER_STATUS"
    }
    
    return response

def play_media(url): # just for testing purposes
    command = ["mplayer", url]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)    
    return process


session_id = None
transport_id = None

player = False
url = None

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
                    elif message_type == 'CLOSE':
                        newsocket.shutdown(socket.SHUT_RDWR) # TODO
                        newsocket.close()
                    elif message_type == 'LOAD':
                        print("load...")
                        player = True
                        url = parsed_data["media"]["contentId"]
                        process = play_media(url)
                        response = format_message('receiver-0', 'sender-vlc', 'urn:x-cast:com.google.cast.media', json.dumps({'type': 'MEDIA_STATUS', 'status': [], 'requestId': parsed_data["requestId"] }))
                        newsocket.send(response)
                    elif message_type == 'GET_STATUS':
                        if namespace == 'urn:x-cast:com.google.cast.receiver':
                            session_id = str(uuid.uuid4())
                            transport_id = session_id
                            if not player:
                                status = generate_receiver_status(parsed_data["requestId"])
                            else:
                                status = generate_media_status(parsed_data["requestId"], url)    
                        elif namespace == 'urn:x-cast:com.google.cast.media':
                            status = generate_media_status(parsed_data["requestId"])
                        else:
                            print("unknown namespace")
                            print(namespace)
                            print(str(parsed_data))
                            continue  # skip this message
                        response = format_message('receiver-0', 'sender-vlc', namespace, json.dumps(status))
                        newsocket.send(response)
            else:
                break
    finally:
        # Clean up the connection
        newsocket.shutdown(socket.SHUT_RDWR)
        newsocket.close()