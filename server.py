import socket
import sys
from _thread import *

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


def client_thread(connection):
    while True:
        sentence = connection.recv(1024).decode()
        capitalized = sentence.upper()
        connection.sendall(capitalized.encode())
    connection.close()


while True:
    connection_socket, address = server_socket.accept()
    print("Server connected to", address)
    start_new_thread(client_thread, (connection_socket, ))
