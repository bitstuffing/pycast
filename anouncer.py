from zeroconf import ServiceInfo, Zeroconf
import socket
import http.server
import socketserver
import threading

IP = "0.0.0.0"
CAST_IP = "192.168.1.106"  

# mDNS
info = ServiceInfo(
    "_googlecast._tcp.local.",
    "Chromecast-78c41f7a7370bdd192cf515532fc4a81._googlecast._tcp.local.",
    addresses=[socket.inet_aton(CAST_IP)],
    port=8009,
    properties={
        'md': 'Chromecast',
        'fn': 'Kitchen',
        'rs': '',
    },
    server="Chromecast-78c41f7a7370bdd192cf515532fc4a81.local.",
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
            with open('setup/eureka_info', 'rb') as file:
                self.wfile.write(file.read())
        else:
            self.send_response(404)
            self.end_headers()

with socketserver.TCPServer((IP, 8008), DIALHandler) as httpd:
    print("serving at port", 8008)
    httpd_thread = threading.Thread(target=httpd.serve_forever)
    httpd_thread.start()

    try:
        while True: # TODO review that
            pass
    except KeyboardInterrupt:
        pass
    finally:
        zeroconf.unregister_service(info)
        zeroconf.close()
        httpd.shutdown()
        httpd_thread.join()
