from ping3 import ping
import socket
import concurrent.futures
import requests
import xml.etree.ElementTree as ET
from messenger import *
import codecs
import json
import ssl

chromecasts = []

SENDER_NAME = "sender-0"
BIG_BUCK_BUNNY_VIDEO = "http://fling.infthink.com/droidream/samples/BigBuckBunny.mp4"

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
    for port in [8008]: #8009
        try:
            response = requests.get(f'http://{ip}:{port}/ssdp/device-desc.xml', headers=headers)
            chromecast_info = parse_chromecast_info(response.text)
            if 'Chromecast' in response.text:
                return chromecast_info
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


def search_device():
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        ip_futures = {executor.submit(is_active, socket.inet_ntoa((ip_int).to_bytes(4, 'big'))): ip_int for ip_int in range(int.from_bytes(socket.inet_aton('192.168.1.0'), 'big'), int.from_bytes(socket.inet_aton('192.168.1.255'), 'big'))}
        for future in concurrent.futures.as_completed(ip_futures):
            ip, active = future.result()
            if active:
                print(f"Active IP: {ip}")
                port_futures = {executor.submit(scan, ip, port): (ip, port) for port in [8008, 8009]}
                for future in concurrent.futures.as_completed(port_futures):
                    ip, port, open = future.result()
                    if open:
                        print(f"Open port: {ip}:{port}")
                        chromecasts.append(detect_chromecasts(ip))
'''
This method is used to study chromecast protocol
'''
def go_chromecast(chromecast):
    app_id = APP_MEDIA_RECEIVER  
    media_url = BIG_BUCK_BUNNY_VIDEO
    content_type = "video/mp4"
    source_id = SENDER_NAME
    destination_id = chromecast["friendlyName"]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_s:
        raw_s.connect((chromecast['ip'], 8009))
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        s = context.wrap_socket(raw_s, server_hostname=chromecast['ip'])

        s.sendall(format_connect_message(source_id, destination_id))
        
        response = s.recv(4096)
        response_data = extract_message(response)
        print("Response after CONNECT:", response_data)

        if not response_data or "sessionId" not in response_data or "transportId" not in response_data:
            print("Invalid response data")
            return

        session_id = response_data.get("sessionId")[0]  
        print("Session ID:", session_id)
        transport_id = response_data.get("transportId")[0]
        print("Transport ID:", transport_id)
        
        s.sendall(format_launch_message(source_id, destination_id, app_id))
        response = s.recv(4096)
        response_data = extract_message(response)
        print("Response after LAUNCH:", response_data)

        s.sendall(format_media_connect_message(source_id, destination_id, transport_id))
        response = s.recv(4096)
        response_data = extract_message(response)
        print("Response after MEDIA CONNECT:", response_data)

        s.sendall(format_load_message(source_id, destination_id, transport_id, media_url, content_type))
        response = s.recv(4096)
        response_data = extract_message(response)
        print("Response after LOAD:", response_data)


if __name__ == '__main__':
    search_device()
    for chromecast in chromecasts:
        status = go_chromecast(chromecast)  
        print(f"Status for {chromecast['friendlyName']}: {status}")
