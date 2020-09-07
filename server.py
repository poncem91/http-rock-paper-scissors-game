import glob
import json
import os
import socket
import sys
from _thread import *


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
    print("Player is connected with address", player_address)
    client_request = connection.recv(1024).decode("utf-8")
    print(player_address, "sent:")
    print(client_request)

    # parses HTTP request
    request_list = client_request.split()
    request_method = request_list[0]
    full_request_url = request_list[1]
    request_url = full_request_url.split("?")[0]

    response_ok_header = "HTTP/1.1 200 OK\r\n"
    response_text_content_header = "Content-Type: text/html\r\n\r\n"
    response_json_content_header = "Content-Type: application/json\r\n\r\n"

    if request_url == "/game":
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
                    print("Unexpected number of players. New player denied.")
                    return
                game_data["player_count"] += 1

            with open("game/data.json", "w") as game_file:
                json.dump(game_data, game_file)
        print("Player number", game_data["player_count"], "has been saved")

        if game_data["player_count"] == 1:
            print("Waiting for second player...")

        response = response_ok_header + response_text_content_header + str(game_data["player_count"])

    elif request_url == "/game/quit":
        clear_game_env()
        connection.sendall((response_ok_header + response_text_content_header).encode("utf-8"))
        connection.close()
        return

    elif request_url == "/game/data.json":
        with open("game/data.json", "r") as game_file:
            game_data = json.load(game_file)
            response = response_ok_header + response_json_content_header + json.dumps(game_data)

    elif "/game/play" in request_url:

        # POST request to /play path will set a move for the play
        if request_method == "POST":
            params = full_request_url.split("?")[1].split("&")
            try:
                play_id = params[0].split("=")[1]
                player_id = int(params[1].split("=")[1])
                move = params[2].split("=")[1]
            except IndexError:
                print("Missing parameters")
                return

            file_path = "game/play/" + play_id + ".json"

            if os.path.isfile(file_path):
                with open(file_path, "r") as play_file:
                    play_data = json.load(play_file)
            else:
                play_data = {"moves": [None, None], "result": [None, None]}

            # only allows the move to be updated if there isn't a move for that play yet
            if play_data["moves"][player_id - 1] is None:

                # sets current play's move
                play_data["moves"][player_id - 1] = move

                # updates file
                with open(file_path, "w") as play_file:
                    json.dump(play_data, play_file)

                print("Current play updated to... ", end='')
                print(play_data["moves"])

                response = response_ok_header + response_text_content_header

                # if both plays are in it calculates the result and updates game file
                if play_data["moves"][0] is not None and play_data["moves"][1] is not None:
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
                    with open(file_path, "w") as play_file:
                        json.dump(play_data, play_file)

                    # updates game score
                    with open("game/data.json", "r") as game_file:
                        game_data = json.load(game_file)
                    game_data["player_1"][result[0]] += 1
                    game_data["player_2"][result[1]] += 1
                    with open("game/data.json", "w") as game_file:
                        json.dump(game_data, game_file)

            # otherwise it sends a 409 error code
            else:
                response = "HTTP/1.1 409 Conflict\r\nContent-Type: text/html\r\n\r\n"

        # GET request to /play path will return the play score
        elif request_method == "GET":
            file_path = request_url[1:]

            if not os.path.isfile(file_path):
                response = "HTTP/1.1 404 Not Found\r\n\r\n"
                connection.sendall(response.encode("utf-8"))
                connection.close()
                return

            with open(file_path, "r") as play_file:
                play_data = json.load(play_file)

            response = response_ok_header + response_json_content_header + json.dumps(play_data)

    # 404 error code sent if a request has been sent to an non-existing resource
    else:
        response = "HTTP/1.1 404 Not Found\r\n\r\n"

    connection.sendall(response.encode("utf-8"))
    connection.close()


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


if __name__ == "__main__":
    main()
