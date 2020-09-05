import socket
import sys

game_started = False
play_count = 0

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

if len(sys.argv) < 3:
    sys.exit("Missing port number and/or address")
try:
    server_port = int(sys.argv[2])
except ValueError:
    sys.exit("Invalid port number")
server_name = socket.gethostbyname(sys.argv[1])

client_socket.connect((server_name, server_port))


def get_request(url):
    return "GET " + url + " HTTP/1.1\r\nHost: " + server_name + "\r\nAccept: text/html\r\n\r\n"


print("Welcome to a game of Rock, Paper, Scissors!")

while True:
    if not game_started:
        client_socket.sendall(get_request("/start-game").encode("utf-8"))
        http_response = client_socket.recv(1024)
        response_status = http_response[1]
        if response_status == "200":
            game_started = True

    input_client = input("Commands:\nR - Rock\nP - Paper\nS - Scissors\nRESET - Reset Game\nQ - Quit\n")

    if input_client.upper() == "Q":
        client_socket.sendall(get_request("/quit-game").encode("utf-8"))
        break

    elif input_client.upper() == "R":
        pass

    elif input_client.upper() == "S":
        client_socket.sendall(input_client.encode("utf-8"))
    response = client_socket.recv(1024)
    print('from server: ', response.decode("utf-8"))
    input_client = input("Say something ")

client_socket.close()
