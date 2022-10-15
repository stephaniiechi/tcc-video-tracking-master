import socket
import os

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Connect the socket to the port where the server is listening
sock.bind(('localhost', 10000))

while True:
    data, addr = sock.recvfrom(4096)  # buffer size is 1024 bytes
    os.system('cls' if os.name == 'nt' else "printf '\033c'")
    print('received {}'.format(data.decode()))
