import socket
import sys
from _thread import *
import pickle
import os
import time


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

    # deletes game data file from previous game if it exists
    if os.path.isfile("game_file.txt"):
        os.remove("game_file.txt")

    while True:
        connection_socket, address = server_socket.accept()
        start_new_thread(client_thread, (connection_socket, address))


def client_thread(connection, player_address):
    print("Player is connected with address", player_address)
    while True:
        client_request = connection.recv(1024).decode("utf-8")
        if not client_request:
            break

        # parses HTTP request
        request_list = client_request.split()
        request_method = request_list[0]
        full_request_url = request_list[1]
        request_url = full_request_url.split("?")[0]

        # if parameters have been passed as a query string it stores them separately
        if len(full_request_url.split("?")) > 1:
            request_url_params = full_request_url.split("?")[1]

        print(player_address, "sent a", request_method, "request to", request_url)

        response_ok_header = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"

        if request_url == "/start-game":
            if not os.path.isfile("game_file.txt"):
                game_data = {'player_count': 1,
                             'player_1': {'W': 0, 'L': 0, 'T': 0},
                             'player_2': {'W': 0, 'L': 0, 'T': 0},
                             'current_play': [None, None],
                             'current_play_result': None,
                             'reset': [False, False]}
                with open("game_file.txt", "wb") as game_file:
                    pickle.dump(game_data, game_file)
            else:
                with open("game_file.txt", "rb") as game_file:
                    game_data = pickle.load(game_file)
                    if game_data["player_count"] >= 2:
                        break
                    game_data["player_count"] += 1

                with open("game_file.txt", "wb") as game_file:
                    pickle.dump(game_data, game_file)
            print("Player number", game_data["player_count"], "has been saved")

            if game_data["player_count"] == 1:
                print("Waiting for second player...")

            response = response_ok_header + str(game_data["player_count"])

        elif request_url == "/quit-game":
            if os.path.isfile("game_file.txt"):
                os.remove("game_file.txt")

        elif request_url == "/gamescore":
            with open("game_file.txt", "rb") as game_file:
                game_data = pickle.load(game_file)
                player_1 = get_player_score(1, game_data)
                player_2 = get_player_score(2, game_data)
                response = response_ok_header + player_1 + "\n" + player_2

        elif request_url == "/play":

            # POST request to /play path will set a move for the play
            if request_method == "POST":
                try:
                    request_body = request_list[7]
                except IndexError:
                    print("Missing POST body")
                    break
                params = request_body.split("&")
                player_num = int(params[0].split("=")[1])
                move = params[1].split("=")[1]
                with open("game_file.txt", "rb") as game_file:
                    game_data = pickle.load(game_file)

                # only allows the move to be updated if there isn't a move for that play yet
                if game_data["current_play"][player_num - 1] is None:

                    # sets current play's move
                    game_data["current_play"][player_num - 1] = move

                    # updates file
                    with open("game_file.txt", "wb") as game_file:
                        pickle.dump(game_data, game_file)

                    print("Current play updated to... ", end='')
                    print(game_data["current_play"])

                    response = response_ok_header

                    # if both plays are in it calculates the result and updates game file
                    if game_data["current_play"][0] is not None and game_data["current_play"][1] is not None:
                        player_1_move = game_data["current_play"][0]
                        player_2_move = game_data["current_play"][1]

                        if player_1_move == "R" and player_2_move == "P":
                            result = "L-W"
                        elif player_1_move == "R" and player_2_move == "S":
                            result = "W-L"
                        elif player_1_move == "P" and player_2_move == "R":
                            result = "W-L"
                        elif player_1_move == "P" and player_2_move == "S":
                            result = "L-W"
                        elif player_1_move == "S" and player_2_move == "R":
                            result = "L-W"
                        elif player_1_move == "S" and player_2_move == "P":
                            result = "W-L"
                        else:
                            result = "T-T"

                        # updates player's game score
                        result_player_1 = result.split("-")[0]
                        result_player_2 = result.split("-")[1]
                        game_data["player_1"][result_player_1] += 1
                        game_data["player_2"][result_player_2] += 1
                        game_data["current_play_result"] = result
                        with open("game_file.txt", "wb") as game_file:
                            pickle.dump(game_data, game_file)

                # otherwise it sends a 409 error code
                else:
                    response = "HTTP/1.1 409 Conflict\r\nContent-Type: text/html\r\n\r\n"

            # GET request to /play path will return the play score
            elif request_method == "GET":
                with open("game_file.txt", "rb") as game_file:
                    game_data = pickle.load(game_file)

                if game_data["current_play_result"] is None:
                    print("Waiting for both players to have made a move...")
                    counter = 0
                    while game_data["current_play_result"] is None and counter < 50:
                        time.sleep(3)
                        with open("game_file.txt", "rb") as game_file:
                            game_data = pickle.load(game_file)
                        counter += 1
                    if counter >= 50:
                        print("Error: Request Timeout while waiting for player to make a move")
                        response = "HTTP/1.1 408 Request Timeout\r\nContent-Type: text/html\r\n\r\n"

                if game_data["current_play_result"] is not None:
                    result = game_data["current_play_result"]
                    print("Requested play result is:", result)

                    response = response_ok_header + result

        # 404 error code sent if a request has been sent to an non-existing resource
        else:
            response = "HTTP/1.1 404 Not Found\r\n\r\n"

        connection.sendall(response.encode("utf-8"))
    connection.close()


def get_player_score(num, game_data):
    player = "player_" + str(num)
    return str(game_data[player]["W"]) + "-" + str(game_data[player]["L"]) + "-" + str(game_data[player]["T"])


if __name__ == "__main__":
    main()
