from struct import pack, unpack
import json

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

def format_connect_message(source_id, destination_id):
    namespace = "urn:x-cast:com.google.cast.tp.connection"
    data = json.dumps({"type": "CONNECT"})
    return format_message(source_id, destination_id, namespace, data)

def format_launch_message(source_id, destination_id, app_id):
    namespace = "urn:x-cast:com.google.cast.receiver"
    data = json.dumps({"type": "LAUNCH", "appId": app_id, "requestId": 0})
    return format_message(source_id, destination_id, namespace, data)

def format_media_connect_message(source_id, destination_id, transport_id):
    namespace = "urn:x-cast:com.google.cast.media"
    data = json.dumps({"type": "CONNECT", "transportId": transport_id, "requestId": 0})
    return format_message(source_id, destination_id, namespace, data)

def format_ping_message(source_id, destination_id):
    namespace = "urn:x-cast:com.google.cast.tp.heartbeat"
    data = json.dumps({"type": "PING"})
    return format_message(source_id, destination_id, namespace, data)

def format_pong_message(source_id, destination_id):
    namespace = "urn:x-cast:com.google.cast.tp.heartbeat"
    data = json.dumps({"type": "PONG"})
    return format_message(source_id, destination_id, namespace, data)

def format_load_message(source_id, destination_id, session_id, media_url, content_type, title=None, thumb=None, current_time=0.0, autoplay=False, stream_type="BUFFERED", metadata=None, subtitles_url=None, subtitles_lang="en-US", subtitles_mime="text/vtt", subtitle_id=1):
    namespace = "urn:x-cast:com.google.cast.media"
    payload = {
        "type": "LOAD",
        "sessionId": session_id,
        "media": {
            "contentId": media_url,
            "streamType": stream_type,
            "contentType": content_type,
            "metadata": metadata if metadata is not None else {}
        },
        "autoplay": autoplay,
        "currentTime": current_time,
        "requestId": 0,
    }

    if title is not None:
        payload["media"]["metadata"]["title"] = title

    if thumb is not None:
        payload["media"]["metadata"]["images"] = [{"url": thumb}]

    # Include subtitles if a subtitle URL is provided
    if subtitles_url is not None:
        payload["media"]["tracks"] = [
            {
                "trackId": subtitle_id,
                "type": "TEXT",
                "trackContentId": subtitles_url,
                "trackContentType": subtitles_mime,
                "name": "Subtitles",
                "language": subtitles_lang,
                "subtype": "SUBTITLES",
            }
        ]
        payload["media"]["textTrackStyle"] = {
            "foregroundColor": "#FFFFFFFF",
            "backgroundColor": "#000000FF",
            "fontScale": 1.2,
            "fontStyle": "NORMAL",
            "fontFamily": "Droid Serif",
            "fontGenericFamily": "SERIF",
            "windowColor": "#AA00FFFF",
            "windowRoundedCornerRadius": 10,
            "windowType": "ROUNDED_CORNERS",
        }

    return format_message(source_id, destination_id, namespace, json.dumps(payload))


def format_get_status_message(source_id, destination_id):
    namespace = "urn:x-cast:com.google.cast.media"
    payload = {
        "type": "GET_STATUS",
        "requestId": 0
    }
    return format_message(source_id, destination_id, namespace, json.dumps(payload))


def format_play_message(source_id, destination_id, sessionId):
    namespace = "urn:x-cast:com.google.cast.media"
    payload = {
        "type": "PLAY",
        "requestId": 0,
        "sessionId": sessionId
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

import struct

import re

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
        return None
