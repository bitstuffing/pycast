import socket
import ssl
import traceback
import cast_channel_pb2 as pb2 # extracted from -> protoc --python_out=. cast_channel.proto

CHROMECAST_IP = "192.168.1.1"  # TODO: change this with the main scanner
CHROMECAST_PORT = 8009  

# data mock captured to test, TODO change that to a file with binary data
data = b'\x00\x00\x00\\\x08\x00\x12\x08sender-0\x1a\nreceiver-0"(urn:x-cast:com.google.cast.tp.deviceauth(\x01:\x16\n\x14\x12\x10-.R\xbf\x1b\xc6\xc4 |\xc6s7\x0b$\xcc\xb0\x18\x01'

try:
    # connect to chromecast
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_s:
        raw_s.connect((CHROMECAST_IP, CHROMECAST_PORT))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        s = context.wrap_socket(raw_s, server_hostname = CHROMECAST_IP)

        s.sendall(data)

        response = s.recv(1024)

        print("Respuesta recibida: ", response)

        msg = pb2.AuthChallenge()
        msg.ParseFromString(response)



except Exception as e:
    print("Error: ", str(e))
    traceback.print_exc()

finally:
    raw_s.close()
