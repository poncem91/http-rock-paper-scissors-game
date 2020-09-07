import glob
import json
import os
import socket
import sys
from _thread import *

RESPONSE_OK_HEADER = "HTTP/1.1 200 OK\r\n"
RESPONSE_TEXT_CONTENT_HEADER = "Content-Type: text/html\r\n\r\n"
RESPONSE_JSON_CONTENT_HEADER = "Content-Type: application/json\r\n\r\n"
RESPONSE_CONFLICT = "HTTP/1.1 409 Conflict\r\nContent-Type: text/html\r\n\r\n"
RESPONSE_NOT_FOUND = "HTTP/1.1 404 Not Found\r\n\r\n"
RESPONSE_BAD_REQUEST = "HTTP/1.1 400 Bad Request\r\n\r\n"


def main():
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

    clear_game_env()

    while True:
        connection_socket, address = server_socket.accept()
        start_new_thread(client_thread, (connection_socket, address))


def client_thread(connection, player_address):
    client_request = connection.recv(1024).decode("utf-8")

    # parses HTTP request
    request_list = client_request.split()
    request_method = request_list[0]
    full_request_url = request_list[1]
    request_url = full_request_url.split("?")[0]

    if request_url == "/game":
        if request_method == "GET":
            start_game(connection, player_address, client_request)
            return

        elif request_method == "DELETE":
            clear_game_env()
            response = RESPONSE_OK_HEADER + RESPONSE_TEXT_CONTENT_HEADER
            connection.sendall(response.encode("utf-8"))
            connection.close()
            print_server_log(player_address, client_request, response)
            return

    elif request_url == "/game/data.json":
        send_file(connection, player_address, client_request, "game/data.json")
        return

    elif "/game/play" in request_url:

        # POST request to /play path will set a move for the play
        if request_method == "POST":
            params = full_request_url.split("?")[1].split("&")
            make_move(connection, player_address, client_request, params)
            return

        # GET request to /play path will return the play score
        elif request_method == "GET":
            file_path = request_url[1:]
            send_file(connection, player_address, client_request, file_path)
            return

    # 404 error code sent if a request has been sent to an non-existing resource
    else:
        connection.sendall(RESPONSE_NOT_FOUND.encode("utf-8"))
        connection.close()
        print_server_log(player_address, client_request, RESPONSE_NOT_FOUND)
        return


def get_player_score(num, game_data):
    player = "player_" + str(num)
    return str(game_data[player]["W"]) + "-" + str(game_data[player]["L"]) + "-" + str(game_data[player]["T"])


def clear_game_env():
    # deletes game data files from previous game if they exist
    files = glob.glob("game/play/*")
    for file in files:
        os.remove(file)
    if os.path.isfile("game/data.json"):
        os.remove("game/data.json")


def print_server_log(address, request, response):
    request_first_line = request.split("\r\n")[0]
    response_status_code = response.split()[1]
    console_log = str(address) + " - '" + request_first_line + "' " + response_status_code
    print(console_log)


def start_game(connection, address, request):
    if not os.path.isfile("game/data.json"):
        game_data = {'player_count': 1,
                     'player_1': {'W': 0, 'L': 0, 'T': 0},
                     'player_2': {'W': 0, 'L': 0, 'T': 0},
                     'reset': [False, False]}
        with open("game/data.json", "w") as game_file:
            json.dump(game_data, game_file)
    else:
        with open("game/data.json", "r") as game_file:
            game_data = json.load(game_file)
            if game_data["player_count"] >= 2:
                response = RESPONSE_CONFLICT + "Too many connected players."
                connection.sendall(response.encode("utf-8"))
                connection.close()
                print_server_log(address, request, response)
                return
            game_data["player_count"] += 1

        with open("game/data.json", "w") as game_file:
            json.dump(game_data, game_file)

    response = RESPONSE_OK_HEADER + RESPONSE_TEXT_CONTENT_HEADER + str(game_data["player_count"])
    connection.sendall(response.encode("utf-8"))
    connection.close()
    print_server_log(address, request, response)


def make_move(connection, address, request, params):
    try:
        play_id = params[0].split("=")[1]
        player_id = int(params[1].split("=")[1])
        move = params[2].split("=")[1]
    except IndexError:
        connection.sendall(RESPONSE_BAD_REQUEST.encode("utf-8"))
        connection.close()
        print_server_log(address, request, RESPONSE_BAD_REQUEST)
        return

    file_path = "game/play/" + play_id + ".json"

    if os.path.isfile(file_path):
        with open(file_path, "r") as play_file:
            play_data = json.load(play_file)
    else:
        play_data = {"moves": [None, None], "result": [None, None], "done": False}

    # only allows the move to be updated if there isn't a move for that play yet
    if play_data["moves"][player_id - 1] is None:

        # sets current play's move
        play_data["moves"][player_id - 1] = move

        # updates file
        with open(file_path, "w") as play_file:
            json.dump(play_data, play_file)

        print("Current play updated to... ", end='')
        print(play_data["moves"])

        response = RESPONSE_OK_HEADER + RESPONSE_TEXT_CONTENT_HEADER
        connection.sendall(response.encode("utf-8"))
        connection.close()
        print_server_log(address, request, response)

        # if both plays are in it calculates the result and updates game file
        if play_data["moves"][0] is not None and play_data["moves"][1] is not None:
            process_play(file_path, play_data)

    # otherwise it sends a 409 error code
    else:
        connection.sendall(RESPONSE_CONFLICT.encode("utf-8"))
        connection.close()
        print_server_log(address, request, RESPONSE_CONFLICT)


def process_play(file_path, play_data):
    player_1_move = play_data["moves"][0]
    player_2_move = play_data["moves"][1]

    if player_1_move == "R" and player_2_move == "P":
        result = ["L", "W"]
    elif player_1_move == "R" and player_2_move == "S":
        result = ["W", "L"]
    elif player_1_move == "P" and player_2_move == "R":
        result = ["W", "L"]
    elif player_1_move == "P" and player_2_move == "S":
        result = ["L", "W"]
    elif player_1_move == "S" and player_2_move == "R":
        result = ["L", "W"]
    elif player_1_move == "S" and player_2_move == "P":
        result = ["W", "L"]
    else:
        result = ["T", "T"]

    # updates play result
    play_data["result"] = result
    play_data["done"] = True
    with open(file_path, "w") as play_file:
        json.dump(play_data, play_file)

    # updates game score
    with open("game/data.json", "r") as game_file:
        game_data = json.load(game_file)
    game_data["player_1"][result[0]] += 1
    game_data["player_2"][result[1]] += 1
    with open("game/data.json", "w") as game_file:
        json.dump(game_data, game_file)


def send_file(connection, address, request, file_path):
    if not os.path.isfile(file_path):
        connection.sendall(RESPONSE_NOT_FOUND.encode("utf-8"))
        connection.close()
        print_server_log(address, request, RESPONSE_NOT_FOUND)
        return

    with open(file_path, "r") as play_file:
        data_file = json.load(play_file)

    response = RESPONSE_OK_HEADER + RESPONSE_JSON_CONTENT_HEADER + json.dumps(data_file)
    connection.sendall(response.encode("utf-8"))
    connection.close()
    print_server_log(address, request, response)


if __name__ == "__main__":
    main()
