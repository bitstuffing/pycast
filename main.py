from ping3 import ping
import socket
import concurrent.futures
import requests
import xml.etree.ElementTree as ET
from messenger import *
import codecs
import json
import ssl
import ipaddress
import subprocess
import sys


def ip_to_network(ip):
    parts = ip.split('.')
    parts[-1] = '0'
    network = '.'.join(parts)
    return network

def get_local_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        IP = s.getsockname()[0]
    finally:
        s.close()
    return IP

def get_network_range():
    ip_address = get_local_ip_address()
    network = ip_to_network(ip_address)
    broadcast = network[:-1] + '255' # TODO, now it's class C, change that
    return network, broadcast


NETWORKING, BROADCAST = get_network_range()

SENDER_NAME = "sender-0"
RECEIVER_NAME = "receiver-0"
BIG_BUCK_BUNNY_VIDEO = "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
MIMETYPE_VIDEO = "video/mp4"
MIMETYPE_VIDEO_URL = "application/x-mpegURL"
MIMETYPE_AAC = "audio/aac"
TVE1_STREAM = "https://ztnr.rtve.es/ztnr/1688877.m3u8"
TELEMADRID_STREAM = "https://new-international-23-secure2.akamaized.net/index.m3u8"

def is_active(ip):
    try:
        delay = ping(ip, timeout=1)
        if delay is not None:
            return ip, True
        else:
            return ip, False
    except:
        return ip, False

def scan(ip, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((ip, port))
            return ip, port, True
        except:
            return ip, port, False
        
def detect_chromecasts(ip):
    headers = {
        'User-Agent': 'curl/7.54.0',
    }
    # TODO change that to not use a loop, it's just one port
    for port in [8008, 8009]: #8009
        try:
            response = requests.get(f'http://{ip}:{port}/ssdp/device-desc.xml', headers=headers)
            res = response.text
            if 'Chromecast' in res:
                print("Using SSDP")
                chromecast_info = parse_chromecast_info(res)
                return chromecast_info
            else:
                print("Using eureka Info")
                response = requests.get(f'http://{ip}:{port}/setup/eureka_info', headers=headers)
                res = response.text
                if '"name":"' in res:
                    chromecast_info = json.loads(res)
                    return {
                        'ip': chromecast_info['ip_address'],
                        'friendlyName': chromecast_info['name']
                    }
        except requests.exceptions.RequestException:
            pass

    return None

def parse_chromecast_info(response_text):
    root = ET.fromstring(response_text)

    namespace = {'ns': 'urn:schemas-upnp-org:device-1-0'}
    friendly_name = root.find('.//ns:friendlyName', namespace).text
    model_name = root.find('.//ns:modelName', namespace).text
    udn = root.find('.//ns:UDN', namespace).text
    ip = root.find('.//ns:URLBase', namespace).text.split('//')[1].split(':')[0]
    return {
        'ip': ip,
        'friendlyName': friendly_name,
        'modelName': model_name,
        'UDN': udn,
    }


def search_device(req = None):
    chromecasts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        if req != None and "." in req:
            ip_futures = {executor.submit(is_active, req): req}
        else:
            ip_futures = {executor.submit(is_active, socket.inet_ntoa((ip_int).to_bytes(4, 'big'))): ip_int for ip_int in range(int.from_bytes(socket.inet_aton(NETWORKING), 'big'), int.from_bytes(socket.inet_aton(BROADCAST), 'big'))}
        for future in concurrent.futures.as_completed(ip_futures):
            ip, active = future.result()
            if active:
                print(f"Active IP: {ip}")
                port_futures = {executor.submit(scan, ip, port): (ip, port) for port in [8008, 8009]}
                for future in concurrent.futures.as_completed(port_futures):
                    ip, port, open = future.result()
                    if open:
                        print(f"Open port: {ip}:{port}")
                        detected_chromecast = detect_chromecasts(ip)
                        if req != None and "." not in req and detected_chromecast!=None and detected_chromecast["friendlyName"] == req:
                            chromecasts.append(detected_chromecast)
                        elif req == None or "." in req:
                            chromecasts.append(detected_chromecast)
    return chromecasts
'''
This method is used to study chromecast protocol
'''
def go_chromecast(chromecast, url=TVE1_STREAM):
    app_id = APP_MEDIA_RECEIVER
    media_url = url
    content_type = MIMETYPE_VIDEO_URL
    source_id = SENDER_NAME
    destination_id = RECEIVER_NAME
    requestId = 1

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_s:
        raw_s.connect((chromecast['ip'], 8009))
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        s = context.wrap_socket(raw_s, server_hostname=chromecast['ip'])
        
        # CONNECT message
        s.sendall(format_connect_message(source_id, destination_id))
        print(f"CONNECT sent to ip {chromecast['ip']}")
        s.sendall(format_get_status_message(source_id, destination_id, requestId))
        requestId += 1
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after GET_STATUS:", response_data)

        session_id = None
        transport_id = None
        while(not session_id):
            print("sending LAUNCH")
            s.sendall(format_launch_message(source_id, destination_id, app_id, requestId))
            requestId += 1
            response = s.recv(4096)
            response_data = parse_cast_response(response)
            print("Response after LAUNCH:", response_data)
            if not response_data or "status" not in response_data or "applications" not in response_data["status"]:
                print("Invalid response data, try again")
            else:
                session_id = response_data["status"]["applications"][0]["sessionId"]  
                print("Session ID:", session_id)
                transport_id = response_data["status"]["applications"][0]["transportId"]
                print("Transport ID:", transport_id)

        print("continue...")
        destination_id = transport_id
        # CONNECT message other time
        s.sendall(format_connect_message(source_id, destination_id))
        print(f"re-CONNECT sent to ip {chromecast['ip']}")
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after re-CONNECT:", response_data)
        
        s.sendall(format_load_message(source_id, destination_id, session_id, media_url, content_type, autoplay=False, requestId=requestId, namespace='urn:x-cast:com.google.cast.media'))
        requestId += 1
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after LOAD:", response_data)

        s.sendall(format_get_status_message(source_id, destination_id, requestId))
        requestId += 1
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after GET_STATUS:", response_data)
        media_session_id = response_data["status"][0]["mediaSessionId"]

        s.sendall(format_play_message(source_id, destination_id, media_session_id, requestId=requestId))
        requestId += 1
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after PLAY:", response_data)

if __name__ == '__main__':
    # get parameters from terminal
    if len(sys.argv) == 1:
        # no parameters provided
        ip = None
        url = TVE1_STREAM
    elif len(sys.argv) == 2:
        # one parameter - check if IP or URL
        # Check if param starts with http, if not treat as IP
        if sys.argv[1].startswith('http'):
            ip = None
            url = sys.argv[1]
        else:
            ip = sys.argv[1]
            url = TVE1_STREAM
        
    else:
        # both parameters provided
        if "http" in sys.argv[2]:
            ip = sys.argv[1]
            url = sys.argv[2]
        else:
            ip = sys.argv[2]
            url = sys.argv[1]
    chromecasts = search_device(ip)
    for chromecast in chromecasts:
        status = go_chromecast(chromecast, url)  
        print(f"Status for {chromecast['friendlyName']} in ip {chromecast['ip']}: {status}")
        break
            

