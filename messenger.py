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
    namespace = "urn:x-cast:com.google.cast.receiver"
    data = json.dumps({"type": "CONNECT", "origin" : {}})
    return format_message(source_id, destination_id, namespace, data)

def format_launch_message(source_id, destination_id, app_id):
    namespace = "urn:x-cast:com.google.cast.receiver"
    data = json.dumps({"type": "LAUNCH", "appId": app_id, "requestId": 1})
    return format_message(source_id, destination_id, namespace, data)

def format_media_connect_message(source_id, destination_id, transport_id):
    namespace = "urn:x-cast:com.google.cast.media"
    data = json.dumps({"type": "CONNECT", "transportId": transport_id, "requestId": 1})
    return format_message(source_id, destination_id, namespace, data)

def format_load_message(source_id, destination_id, transport_id, media_url, content_type):
    namespace = "urn:x-cast:com.google.cast.media"
    data = json.dumps({
        "type": "LOAD",
        "transportId": transport_id,
        "requestId": 1,
        "media": {
            "contentId": media_url,
            "contentType": content_type,
            "streamType": "BUFFERED",
        },
        "autoplay": True,
        "currentTime": 0,
        "customData": {}
    })
    return format_message(source_id, destination_id, namespace, data)

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
    string = data[ptr:string_end_ptr].decode('utf-8')
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