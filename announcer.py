from zeroconf import ServiceInfo, Zeroconf
import socket
import http.server
import socketserver
import socket
import threading
import time
import string
import uuid

IP = "0.0.0.0"
NAME = 'awesome'
ID = "Chromecast-{}".format(NAME)

def get_local_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)) 
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

CAST_IP = get_local_ip_address()

print(CAST_IP)

import random
import string

def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    result = ''.join(random.choices(characters, k=length))
    return result

CAST_ID = generate_random_string(32)
print(CAST_ID)

uuid = str(uuid.uuid4())

# mDNS
info = ServiceInfo(
    "_googlecast._tcp.local.",
    "{}._googlecast._tcp.local.".format(ID),
    addresses=[socket.inet_aton(CAST_IP)],
    port=8009,
    properties={
        'id': 'awesome',
        'cd': CAST_ID,
        'rm': '',
        've': '05',
        'md': 'Chromecast',
        'ic': '/setup/icon.png',
        'fn': NAME,
        'ca': '4101',
        'st': '0',
        'bs': 'FA8FCA843B31',
        'nf': '1',
        'rs': '',
    },
    server="{}.local.".format(ID),
)

zeroconf = Zeroconf()
zeroconf.register_service(info)

# DIAL
class DIALHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print(f"GET request received at {self.path}")
        if self.path == "/setup/eureka_info":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            with open('setup/eureka_info', 'r') as file:
                content = file.read()
            content = content.replace("DUMMY_IP_ADDRESS", get_local_ip_address())
            self.wfile.write(content.encode())
        elif self.path == "/ssdp/device-desc.xml" :
            self.send_response(200)
            self.send_header('Content-type', 'application/xml')
            self.end_headers()
            with open('ssdp/device-desc.xml', 'r') as file:
                content = file.read()
            content = content.replace("DUMMY_IP_ADDRESS", get_local_ip_address())
            self.wfile.write(content.encode())
        else:
            self.send_response(404)
            self.end_headers()

# SSDP
class SSDPServer(socketserver.UDPServer):
    def handle_request(self):
        data, address = self.socket.recvfrom(1024)
        print(f"Received data from {address}: {data}")
        if b"M-SEARCH" in data:
            response = [
                'HTTP/1.1 200 OK',
                'CACHE-CONTROL: max-age=1800',
                'DATE: ' + time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time())),
                'EXT: ',
                'LOCATION: http://{}:8008/setup/eureka_info'.format(CAST_IP),
                'OPT: "http://schemas.upnp.org/upnp/1/0/"; ns=01',
                '01-NLS: {}'.format(CAST_ID),
                'SERVER: Linux/3.14.0 UPnP/1.0 quick_ssdp/1.0',
                'ST: urn:dial-multiscreen-org:service:dial:1',
                'USN: uuid:{}'.format(uuid),
                'BOOTID.UPNP.ORG: 7339',
                'CONFIGID.UPNP.ORG: 7339',
                '',
                '',
            ]
            self.socket.sendto('\r\n'.join(response).encode(), address)

with socketserver.TCPServer((IP, 8008), DIALHandler) as httpd:
    print("serving at port", 8008)
    ssdp = SSDPServer((IP, 1900), SSDPServer)

    httpd_thread = threading.Thread(target=httpd.serve_forever)
    httpd_thread.start()

    ssdp_thread = threading.Thread(target=ssdp.serve_forever)
    ssdp_thread.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass
    finally:
        zeroconf.unregister_service(info)
        zeroconf.close()
        httpd.shutdown()
        httpd_thread.join()
        ssdp.shutdown()
        ssdp_thread.join()
