import socket
import ssl
import json
import re
from messenger import *
import uuid
import sys
import subprocess
import signal
import threading

import logging
logging.basicConfig(level=logging.DEBUG)

newsocket = None
sock = None

def signal_handler(signal, frame):
    print('Ctrl+C pressed! Closing the socket.')
    try:
        if newsocket:
            newsocket.shutdown(socket.SHUT_RDWR)
            newsocket.close()
        if sock:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
    except:
        pass
    sys.exit(0)

# signal handler
signal.signal(signal.SIGINT, signal_handler)

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

def play_media(url):
    command = ["vlc", url]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    t = threading.Timer(4.0, process.kill)
    t.start()
    stdout, stderr = process.communicate()
    t.cancel()
    return stdout, stderr

session_id = None
transport_id = None

player = False
url = None

while True:
    newsocket = None
    fromaddr = None
    try:
        # Accept a connection
        newsocket, fromaddr = ssl_sock.accept()
    except ssl.SSLError as e:
        print(f"SSL error occurred: {e}")
        if newsocket:
            newsocket.shutdown(socket.SHUT_RDWR)
            newsocket.close()
        continue
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
        if newsocket:
            newsocket.shutdown(socket.SHUT_RDWR)
            newsocket.close()
        continue
    try:
        print('Accepted connection from', fromaddr)
        
        # Receive data and print it out
        while True:
            try:
                data = newsocket.recv(1024)
            except:
                newsocket.shutdown(socket.SHUT_RDWR) 
                newsocket.close()
                sock.close()
            if data:
                print('Received:', data)
                
                try:
                    parsed_data = parse_cast_response(data)
                except Exception as e:
                    print(f"Error parsing data: {e}")
                    continue
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
                        response = format_message('receiver-0', 'sender-0', 'urn:x-cast:com.google.cast.tp.connection', json.dumps({'type': 'CONNECTED'}))
                        newsocket.send(response)
                    elif message_type == 'PING':
                        print("ping...")
                        response = format_message('receiver-0', 'sender-0', 'urn:x-cast:com.google.cast.tp.heartbeat', json.dumps({'type': 'PONG'}))
                        newsocket.send(response)
                    elif message_type == 'CLOSE':
                        newsocket.shutdown(socket.SHUT_RDWR) # TODO
                        newsocket.close()
                    elif message_type == 'LOAD':
                        print("load...")
                        player = True
                        url = parsed_data["media"]["contentId"]
                        process = play_media(url)
                        response = format_message('receiver-0', 'sender-0', 'urn:x-cast:com.google.cast.media', json.dumps({'type': 'MEDIA_STATUS', 'status': [], 'requestId': parsed_data["requestId"] }))
                        newsocket.send(response)
                    elif message_type == 'GET_STATUS':
                        if namespace == 'urn:x-cast:com.google.cast.receiver':
                            session_id = str(uuid.uuid4())
                            transport_id = session_id
                            if not player:
                                print("no player")
                                status = generate_receiver_status(parsed_data["requestId"])
                            else:
                                print("player")
                                status = generate_media_status(parsed_data["requestId"], url)    
                        elif namespace == 'urn:x-cast:com.google.cast.media':
                            print("media")
                            status = {'type': 'MEDIA_STATUS', 'status': [], 'requestId': parsed_data["requestId"] }
                        else:
                            print("unknown namespace")
                            print(namespace)
                            print(str(parsed_data))
                            continue  # skip this message
                        response = format_message('receiver-0', 'sender-0', namespace, json.dumps(status))
                        newsocket.send(response)
                    elif message_type == 'CLOSE':
                        print("close...")
                        newsocket.shutdown(socket.SHUT_RDWR)
                        newsocket.close()
                        sock.shutdown(socket.SHUT_RDWR)
                        sock.close()
                        sys.exit(0)
                    else:
                        print("unknown message type")
                        print(str(parsed_data))
                        continue
                else:
                    if namespace == "urn:x-cast:com.google.cast.tp.deviceauth":
                        print("device auth...")
                        session_id = str(uuid.uuid4())
                        transport_id = session_id
                        response = format_auth_message('receiver-0', 'sender-0', session_id, transport_id)
                        newsocket.send(response)
                    elif namespace == 'urn:x-cast:com.google.cast.tp.heartbeat':
                        print("heartbeat...")
                        response = format_message('receiver-0', 'sender-0', 'urn:x-cast:com.google.cast.tp.heartbeat', json.dumps(
                            {'type': 'PONG'}
                        ))
                        newsocket.send(response)
                    else:
                        print("unknown message")
                        print(namespace)
                        continue
            else:
                break
    finally:
        if newsocket:
            newsocket.shutdown(socket.SHUT_RDWR)
            newsocket.close()