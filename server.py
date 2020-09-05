import socket
import sys
from _thread import *
import time

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


def client_thread(connection, player_address):
    print("Player is connected with address", player_address)
    while True:
        request = connection.recv(1024).decode("utf-8")
        if not request:
            break
        request_list = request.split(' ')
        request_method = request_list[0]
        request_url = request_list[1]
        print("Player", player_address, "sent a", request_method, "request to", request_url)
        response_ok_header = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"

        if request_url == "/start-game":
            with open("game_file.txt", "r") as game_file:
                count = len(game_file.readlines())
            with open("game_file.txt", "a+") as game_file:
                count += 1
                game_file.write(str(count) + "\n")
                print("Player number", count, "has been saved")

            if count == 1:
                print("Waiting for second player...")

            response = response_ok_header

        if request_url == "/quit-game":
            open("game_file.txt", "w").close()

        if request_url == "/gamescore":
            with open("game_file.txt", "r") as game_file:
                response = response_ok_header + game_file.read() + "\r\n\r\n"

        connection.sendall(response.encode("utf-8"))
    connection.close()


while True:
    connection_socket, address = server_socket.accept()
    start_new_thread(client_thread, (connection_socket, address))
