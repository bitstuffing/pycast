from struct import pack, unpack
from urllib.parse import quote, unquote
import json
import re
import uuid
import json
import re
import subprocess
import threading
import time
import socket

# app ids
APP_BACKDROP = "E8C28D3C"
APP_YOUTUBE = "233637DE"
APP_MEDIA_RECEIVER = "CC1AD845"
APP_PLEX = "06ee44ee-e7e3-4249-83b6-f5d0b6f07f34_1"
APP_DASHCAST = "84912283"
APP_HOMEASSISTANT_LOVELACE = "A078F6B0"
APP_HOMEASSISTANT_MEDIA = "B45F4572"
APP_SUPLA = "A41B766D"
APP_YLEAREENA = "A9BCCB7C"
APP_BUBBLEUPNP = "3927FA74"
APP_BBCSOUNDS = "03977A48"
APP_BBCIPLAYER = "5E81F6DB"

session_id = ""
transport_id = ""
global player,vlc_process
player = False
vlc_process = None
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1788.0"

headers = {
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}


def generate_media_status(requestId=0, contentId=None, playerState="IDLE", currentTime=0):
    if contentId:
        parsed_url = contentId.split('?')
        base_url = parsed_url[0]
        params = parsed_url[1] if len(parsed_url) > 1 else ""
        
        if params:
            encoded_contentId = contentId
        else:
            encoded_contentId = quote(base_url, safe=':/?=&%')
    else:
        encoded_contentId = "https://example.com/default.m3u8"

    response = {
        "requestId": requestId,
        "status": [{
            "mediaSessionId": 1,
            "playbackRate": 1,
            "playerState": playerState,
            "currentTime": currentTime,
            "supportedMediaCommands": 12303,
            "volume": {
                "level": 1,
                "muted": False
            },
            "media": {
                "contentId": encoded_contentId,
                "streamType": "BUFFERED",
                "contentType": "application/x-mpegURL",
                "metadata": {},
                "customData": {
                    "headers": headers
                }
            },
            "currentItemId": 1,
            "extendedStatus": {
                "playerState": playerState,
                "media": {
                    "contentId": encoded_contentId,
                    "streamType": "BUFFERED",
                    "contentType": "application/x-mpegURL",
                    "metadata": {}
                },
                "mediaSessionId": 1
            },
            "repeatMode": "REPEAT_OFF"
        }]
    }
    
    return response

def update_media_status(conn, interval=5):
    global player, url, current_time
    while player:
        time.sleep(interval)
        current_time += interval
        status = generate_media_status(contentId=url, playerState="PLAYING", currentTime=current_time)
        response = format_message('receiver-0', 'sender-0', 'urn:x-cast:com.google.cast.media', json.dumps(status))
        conn.send(response)

def generate_receiver_status(session_id, transport_id, requestId=1):
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


def start_vlc_with_rc(url):
    global vlc_socket
    command = [
        "vlc", "--intf", "rc", "--rc-host", "localhost:5555", "--quiet", url
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # connect to remote VLC
    time.sleep(2)  # wait until start and socket is available
    vlc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    vlc_socket.connect(('localhost', 5555))
    return process

def send_vlc_command(command):
    global vlc_socket
    if vlc_socket:
        try:
            vlc_socket.sendall((command + "\n").encode())
        except Exception as e:
            print(f"Error sending command to VLC: {e}")

def handle_received_data(data, conn):
    global vlc_process, vlc_socket
    print('Received:', data)
    global player, url, current_time, vlc_process
    try:
        parsed_data = parse_cast_response(data)
    except Exception as e:
        print(f"Error parsing data: {e}")
        return

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
            conn.send(response)
        elif message_type == 'PING':
            print("ping...")
            response = format_message('receiver-0', 'sender-0', 'urn:x-cast:com.google.cast.tp.heartbeat', json.dumps({'type': 'PONG'}))
            conn.send(response)
        elif message_type == 'LOAD':
            print("load...")
            if vlc_process is not None:
                send_vlc_command("stop")  # stop without close VLC
            player = True
            url = parsed_data["media"]["contentId"]
            current_time = 0
            threading.Thread(target=update_media_status, args=(conn,), daemon=True).start()  # Iniciar el hilo para actualizar el estado
            if vlc_process is None:
                vlc_process = start_vlc_with_rc(url)  # indicate remote control to VLC
            else:
                send_vlc_command(f"add {url}")  # add new url if VLC is open
            response = format_message('receiver-0', 'sender-0', 'urn:x-cast:com.google.cast.media', json.dumps({'type': 'MEDIA_STATUS', 'status': [], 'requestId': parsed_data["requestId"]}))
            conn.send(response)
        elif message_type == 'GET_STATUS':
            if namespace == 'urn:x-cast:com.google.cast.receiver':
                session_id = str(uuid.uuid4())
                transport_id = session_id
                if not player:
                    print("no player")
                    status = generate_receiver_status(session_id=session_id, transport_id=transport_id, requestId=parsed_data["requestId"])
                else:
                    print("player")
                    status = generate_media_status(parsed_data["requestId"], url, "PLAYING", current_time)    
            elif namespace == 'urn:x-cast:com.google.cast.media':
                print("media")
                status = {'type': 'MEDIA_STATUS', 'status': [], 'requestId': parsed_data["requestId"]}
            else:
                print("unknown namespace")
                print(namespace)
                print(str(parsed_data))
                return  # skip this message
            response = format_message('receiver-0', 'sender-0', namespace, json.dumps(status))
            conn.send(response)
        elif message_type == 'CLOSE':
            print("close...")
            player = False  # stop
            if vlc_process is not None:
                send_vlc_command("quit")  # close VLC (via remote command)
                vlc_process = None
                if vlc_socket:
                    vlc_socket.close()
                    vlc_socket = None
            conn.shutdown()
            sock.close()
            sys.exit(0)
        elif message_type == 'SEEK':
            print("seek...")
            new_time = parsed_data.get('currentTime', 0)
            current_time = new_time
            if vlc_process is not None:
                send_vlc_command(f"seek {current_time}")  # send seek command to VLC
            response = generate_media_status(requestId=parsed_data["requestId"], contentId=url, playerState="PLAYING", currentTime=current_time)
            response_message = format_message('receiver-0', 'sender-0', namespace, json.dumps(response))
            conn.send(response_message)
        else:
            print("unknown message type")
            print(str(parsed_data))
            return
    else:
        if namespace == "urn:x-cast:com.google.cast.tp.deviceauth":
            print("device auth...")
            session_id = str(uuid.uuid4())
            transport_id = session_id
            response = format_auth_message('receiver-0', 'sender-0', session_id, transport_id)
            conn.send(response)
        elif namespace == 'urn:x-cast:com.google.cast.tp.heartbeat':
            print("heartbeat...")
            response = format_message('receiver-0', 'sender-0', 'urn:x-cast:com.google.cast.tp.heartbeat', json.dumps({'type': 'PONG'}))
            conn.send(response)
        else:
            print("unknown message")
            print(namespace)


def format_auth_message(source_id, destination_id, sessionId, transportId):
    namespace = "urn:x-cast:com.google.cast.receiver"
    data = json.dumps({
        'requestId': 1,
        'status': {
            'applications': [{
                'appId': 'E8C28D3C',
                'appType': 'WEB',
                'displayName': 'Backdrop',
                'iconUrl': '',
                'isIdleScreen': True,
                'launchedFromCloud': False,
                'namespaces': [{
                    'name': 'urn:x-cast:com.google.cast.sse'
                }, {
                    'name': 'urn:x-cast:com.google.cast.cac'
                }],
                'sessionId': sessionId,
                'statusText': '',
                'transportId': transportId,
                'universalAppId': 'E8C28D3C'
            }],
            'isActiveInput': False,
            'isStandBy': True,
            'userEq': {},
            'volume': {
                'controlType': 'attenuation',
                'level': 1.0,
                'muted': False,
                'stepInterval': 0.03999999910593033
            }
        },
        'type': 'RECEIVER_STATUS'
    })
    return format_message(source_id, destination_id, namespace, data)

def format_connect_message(source_id, destination_id):
    namespace = "urn:x-cast:com.google.cast.tp.connection"
    data = json.dumps( {'type': 'CONNECT', 'origin': {}})
    return format_message(source_id, destination_id, namespace, data)

def format_launch_message(source_id, destination_id, app_id, requestId):
    namespace = "urn:x-cast:com.google.cast.receiver"
    data = json.dumps({"type": "LAUNCH", "appId": app_id, "requestId": requestId})
    return format_message(source_id, destination_id, namespace, data)

def format_ping_message(source_id, destination_id):
    namespace = "urn:x-cast:com.google.cast.tp.heartbeat"
    data = json.dumps({"type": "PING"})
    return format_message(source_id, destination_id, namespace, data)

def format_pong_message(source_id, destination_id):
    namespace = "urn:x-cast:com.google.cast.tp.heartbeat"
    data = json.dumps({"type": "PONG"})
    return format_message(source_id, destination_id, namespace, data)

def format_load_message(source_id, destination_id, session_id, media_url, content_type="application/x-mpegURL", title=None, thumb=None, current_time=0.0, autoplay=True, stream_type="BUFFERED", metadata=None, subtitles_url=None, subtitles_lang="en-US", subtitles_mime="text/vtt", subtitle_id=1, requestId=0, namespace="urn:x-cast:com.google.cast.media"):
    parsed_url = media_url.split('?')
    base_url = parsed_url[0]
    params = parsed_url[1] if len(parsed_url) > 1 else ""
    
    if params:
        encoded_url = media_url
    else:
        encoded_url = quote(base_url, safe=':/?=&%')

    if metadata is None:
        metadata = {}
    
    payload = {
        "type": "LOAD",
        "sessionId": session_id,
        "media": {
            "contentId": encoded_url,
            "streamType": stream_type,
            "contentType": content_type,
            "metadata": metadata.copy(),
            "customData": {
                "headers": headers
            }
        },
        "autoplay": autoplay,
        "currentTime": current_time,
        "requestId": requestId
    }

    if title:
        payload["media"]["metadata"]["title"] = title

    if thumb:
        payload["media"]["metadata"]["images"] = [{"url": thumb}]

    return format_message(source_id, destination_id, namespace, json.dumps(payload))


def format_get_status_message(source_id, destination_id, requestId, namespace = "urn:x-cast:com.google.cast.receiver"):
    payload = {
        "type": "GET_STATUS",
        "requestId": requestId
    }
    
    return format_message(source_id, destination_id, namespace, json.dumps(payload))


def format_play_message(source_id, destination_id, media_session_id, requestId):
    namespace = "urn:x-cast:com.google.cast.media"
    payload = {
        "type": "PLAY",
        "requestId": requestId,
        "mediaSessionId": media_session_id
    }
    
    return format_message(source_id, destination_id, namespace, json.dumps(payload))

def format_field_id(field_no, field_type):
    return (field_no << 3) | field_type

def format_varint_value(int_value):
    varint_result = bytearray()
    while int_value > 127:
        varint_result.append((int_value & 127) | 128)
        int_value >>= 7
    varint_result.append(int_value & 127)
    return bytes(varint_result)

def format_int_field(field_number, field_data):
    field = pack("B", format_field_id(field_number, 0))  # 0 = Int field type
    field += pack("B", field_data)
    return field

def format_string_field(field_number, field_data):
    field_data = field_data.encode('utf-8')
    field_data_len = format_varint_value(len(field_data))
    field = pack("B", format_field_id(field_number, 2))  # 2 = Length-delimited field type
    field += field_data_len
    field += field_data
    return field

def prepend_length_header(msg):
    return pack(">I", len(msg)) + msg

def format_message(source_id, destination_id, namespace, data):
    msg = bytearray()
    msg += format_int_field(1, 0)  # Protocol Version = 0
    msg += format_string_field(2, source_id)
    if destination_id is not None:
        msg += format_string_field(3, destination_id)
    msg += format_string_field(4, namespace)
    msg += format_int_field(5, 0)  # payload type : string = 0
    if data:
        msg += format_string_field(6, data)
    msg = bytes(msg)
    msg = prepend_length_header(msg)
    return msg

def extract_length_header(msg):
    if len(msg) < 4:
        return None
    len_data = msg[:4]
    remainder = b""
    if len(msg) > 4:
        remainder = msg[4:]
    length = unpack(">I", len_data)[0]
    return length, remainder

def extract_field_id(data):
    byte = data[0]
    return byte >> 3, (byte & 7)

def extract_int_field(data):
    field_id = extract_field_id(data)[0]
    int_value = data[1]
    remainder = b""
    if len(data) > 2:
        remainder = data[2:]
    return field_id, int_value, remainder

def extract_string_field(data):
    field_id = extract_field_id(data)[0]
    length, ptr = decode_varint(data, 1)
    string_end_ptr = ptr + length
    string = data[ptr:string_end_ptr]
    try:
        string = json.loads(string.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    remainder = b""
    if len(data) > string_end_ptr:
        remainder = data[string_end_ptr:]
    return field_id, string, remainder


def decode_varint(data, ptr):
    value = 0
    shift = 0
    while True:
        byte = data[ptr]
        value |= (byte & 127) << shift
        ptr += 1
        if not (byte & 128):
            break
        shift += 7
    return value, ptr

def extract_message(data):
    resp = {}
    while len(data) > 0:
        field_id, field_data, data = extract_string_field(data)
        if field_id in resp:
            resp[field_id].append(field_data)
        else:
            resp[field_id] = [field_data]
    return resp

def parse_cast_response(response):
    decoded_data = response.decode('unicode_escape')

    match = re.search(r'({.*})', decoded_data)
    
    if match:
        # Extract the JSON string from the match
        json_string = match.group(1)
        
        # Decode the JSON string into a Python object
        json_data = json.loads(json_string)
        
        return json_data
    else:
        print("No JSON found in response")
        print(str(decoded_data))
        return None