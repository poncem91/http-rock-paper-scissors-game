import socket
import sys

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

if len(sys.argv) < 3:
    sys.exit("Missing port number and/or address")
try:
    server_port = int(sys.argv[2])
except ValueError:
    sys.exit("Invalid port number")
server_name = socket.gethostbyname(sys.argv[1])

client_socket.connect((server_name, server_port))

input_client = input("Say something ")
while input_client.lower().strip() != 'bye':
    client_socket.sendall(input_client.encode())
    response = client_socket.recv(1024)
    print('from server: ', response.decode())
    input_client = input("Say something ")

client_socket.close()