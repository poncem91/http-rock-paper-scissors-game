import socket
import sys

if len(sys.argv) < 2:
    sys.exit("Missing port number")
try:
    server_port = int(sys.argv[1])
except ValueError:
    sys.exit("Invalid port number")

server_name = socket.gethostbyname(socket.gethostname())

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((server_name, server_port))
server_socket.listen(2)
print("Server", server_name, "at port", server_port, "ready to receive.")

while True:
    connection_socket, address = server_socket.accept()
    sentence = connection_socket.recv(1024).decode()
    capitalized = sentence.upper()
    connection_socket.send(capitalized.encode())
    connection_socket.close()