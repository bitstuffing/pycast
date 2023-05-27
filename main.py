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
RECEIVER_NAME = "receiver-0"
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
    destination_id = RECEIVER_NAME

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_s:
        raw_s.connect((chromecast['ip'], 8009))
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        s = context.wrap_socket(raw_s, server_hostname=chromecast['ip'])
        # CONNECT message
        
        s.sendall(format_connect_message(source_id, destination_id))
        print(f"CONNECT sent to ip {chromecast['ip']}")

        print("sending LAUNCH")
        s.sendall(format_launch_message(source_id, destination_id, app_id))
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after LAUNCH:", response_data)
        if not response_data or "status" not in response_data or "applications" not in response_data["status"]:
            print("Invalid response data, try again")
            return
        
        session_id = response_data["status"]["applications"][0]["sessionId"]  
        print("Session ID:", session_id)
        transport_id = response_data["status"]["applications"][0]["transportId"]
        print("Transport ID:", transport_id)

        '''
        # Connect to the transportId
        s.sendall(format_connect_message(source_id, transport_id))
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after CONNECT to transportId:", response_data)

        s.sendall(format_media_connect_message(source_id, destination_id, transport_id))
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after MEDIA CONNECT:", response_data)
        '''
        '''
        s.sendall(format_get_status_message(source_id, destination_id))
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after GET_STATUS:", response_data)
        '''
        s.sendall(format_load_message(source_id, destination_id, transport_id, media_url, content_type))
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after LOAD:", response_data)
        '''
        if response_data and "type" in response_data and response_data["type"] == "PING":
            s.sendall(format_pong_message(source_id, destination_id))
            response = s.recv(4096)
            response_data = parse_cast_response(response)
            print("Response after PONG:", response_data)
        print("continue...")
        
        s.sendall(format_play_message(source_id, destination_id, session_id))
        response = s.recv(4096)
        response_data = parse_cast_response(response)
        print("Response after PLAY:", response_data)
        '''


if __name__ == '__main__':
    search_device()
    for chromecast in chromecasts:
        if chromecast['ip'] ==  "192.168.1.42": # test with one chromecast
            status = go_chromecast(chromecast)  
            print(f"Status for {chromecast['friendlyName']} in ip {chromecast['ip']}: {status}")
            

