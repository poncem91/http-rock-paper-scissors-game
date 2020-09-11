import glob
import json
import os
import socket
import sys
from _thread import *

RESPONSE_OK_HEADER = "HTTP/1.1 200 OK\r\n"
RESPONSE_TEXT_CONTENT_HEADER = "Content-Type: text/html\r\n"
RESPONSE_JSON_CONTENT_HEADER = "Content-Type: application/json\r\n"
RESPONSE_CONTENT_LENGTH_HEADER = "Content-Length: "
RESPONSE_END_HEADERS = "\r\n\r\n"
RESPONSE_CONFLICT = "HTTP/1.1 409 Conflict\r\n" + RESPONSE_TEXT_CONTENT_HEADER + RESPONSE_CONTENT_LENGTH_HEADER + "0" \
                    + RESPONSE_END_HEADERS
RESPONSE_NOT_FOUND = "HTTP/1.1 404 Not Found\r\n" + RESPONSE_TEXT_CONTENT_HEADER + RESPONSE_CONTENT_LENGTH_HEADER + "0" \
                     + RESPONSE_END_HEADERS
RESPONSE_BAD_REQUEST = "HTTP/1.1 400 Bad Request\r\n" + RESPONSE_TEXT_CONTENT_HEADER + RESPONSE_CONTENT_LENGTH_HEADER \
                       + "0" + RESPONSE_END_HEADERS


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

    # clears any game data that might've been saved from previous games
    clear_game_data()

    while True:
        connection_socket, address = server_socket.accept()
        start_new_thread(client_thread, (connection_socket, address))


def client_thread(connection, player_address):
    client_request = connection.recv(1024).decode("utf-8")

    # parses HTTP request
    request_list = client_request.split()
    request_method = request_list[0]
    full_request_url = request_list[1]  # including any query string parameters
    request_url = full_request_url.split("?")[0]  # not including any query string parameters

    if request_url == "/game":

        # handles GET /game requests
        if request_method == "GET":
            start_game(connection, player_address, client_request)
            return

        # handles DELETE /game requests
        elif request_method == "DELETE":
            if not os.path.isfile("game/data.json"):
                connection.sendall(RESPONSE_NOT_FOUND.encode("utf-8"))
                connection.close()
                print_server_log(player_address, client_request, RESPONSE_NOT_FOUND)
                return

            with open("game/data.json", "r") as game_file:
                game_data = json.load(game_file)

            # checks if both players have issued a reset request before resetting game or allows resets if there is only
            # one player currently in the game
            if game_data["reset"][0] and game_data["reset"][1] or game_data["player_count"] <= 1:
                clear_game_data()
                response = RESPONSE_OK_HEADER + RESPONSE_TEXT_CONTENT_HEADER + RESPONSE_CONTENT_LENGTH_HEADER + "0" \
                           + RESPONSE_END_HEADERS
                connection.sendall(response.encode("utf-8"))
                connection.close()
                print_server_log(player_address, client_request, response)
                return

            # if both players haven't issued a reset request, there is a conflict in the request and sends 409 code
            else:
                connection.sendall(RESPONSE_CONFLICT.encode("utf-8"))
                connection.close()
                print_server_log(player_address, client_request, RESPONSE_CONFLICT)

        elif request_method == "PATCH":

            if not os.path.isfile("game/data.json"):
                connection.sendall(RESPONSE_NOT_FOUND.encode("utf-8"))
                connection.close()
                print_server_log(player_address, client_request, RESPONSE_NOT_FOUND)
                return

            try:
                params = full_request_url.split("?")[1].split("&")
                player_id = params[0].split("=")[1]
                key = client_request.split("\r\n\r\n")[1].split("=")[0]
                value = client_request.split("\r\n\r\n")[1].split("=")[1]
            except IndexError:
                connection.sendall(RESPONSE_BAD_REQUEST.encode("utf-8"))
                connection.close()
                print_server_log(player_address, client_request, RESPONSE_BAD_REQUEST)
                return

            with open("game/data.json", "r") as game_file:
                game_data = json.load(game_file)

            game_data[key][int(player_id) - 1] = value

            with open("game/data.json", "w") as game_file:
                json.dump(game_data, game_file)

            response = RESPONSE_OK_HEADER + RESPONSE_TEXT_CONTENT_HEADER + RESPONSE_CONTENT_LENGTH_HEADER + "0" \
                       + RESPONSE_END_HEADERS
            connection.sendall(response.encode("utf-8"))
            connection.close()
            print_server_log(player_address, client_request, response)
            return

    # handles GET /game/data.json requests
    elif request_url == "/game/data.json":
        send_file(connection, player_address, client_request, "game/data.json")
        return

    # handles requests for /game/play/{play_id}.json
    elif "/game/play" in request_url:

        # handles POST /game/play/{playid}.json requests to make a play move for the specific player
        if request_method == "POST":
            try:
                params = full_request_url.split("?")[1].split("&")
                move = client_request.split("\r\n\r\n")[1].split("=")[1]
            except IndexError:
                connection.sendall(RESPONSE_BAD_REQUEST.encode("utf-8"))
                connection.close()
                print_server_log(player_address, client_request, RESPONSE_BAD_REQUEST)
                return
            make_move(connection, player_address, client_request, request_url, params, move)
            return

        # handles GET /game/play/{play_id}.json requests to get play file
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


# deletes game data files
def clear_game_data():
    files = glob.glob("game/play/*")
    for file in files:
        os.remove(file)
    if os.path.isfile("game/data.json"):
        os.remove("game/data.json")


# prints server request-response logs
def print_server_log(address, request, response):
    request_first_line = request.split("\r\n")[0]
    response_status_code = response.split()[1]
    console_log = str(address) + " - '" + request_first_line + "' " + response_status_code
    print(console_log)


# starts game for player client
def start_game(connection, address, request):
    # creates game data file if it doesn't yet exist
    if not os.path.isfile("game/data.json"):
        game_data = {'player_count': 1,
                     'player_1': {'W': 0, 'L': 0, 'T': 0},
                     'player_2': {'W': 0, 'L': 0, 'T': 0},
                     'reset': [False, False],
                     'finished_plays': 0}
        with open("game/data.json", "w") as game_file:
            json.dump(game_data, game_file)

    # otherwise it updates game file with new player
    else:
        with open("game/data.json", "r") as game_file:
            game_data = json.load(game_file)

        # only allows a maximum of 2 players
        if game_data["player_count"] >= 2:
            connection.sendall(RESPONSE_CONFLICT.encode("utf-8"))
            connection.close()
            print_server_log(address, request, RESPONSE_CONFLICT)
            return

        with open("game/data.json", "w") as game_file:
            game_data["player_count"] += 1
            json.dump(game_data, game_file)

    body_length = len(str(game_data["player_count"]).encode("utf-8"))
    response = RESPONSE_OK_HEADER + RESPONSE_TEXT_CONTENT_HEADER + RESPONSE_CONTENT_LENGTH_HEADER + str(body_length) \
               + RESPONSE_END_HEADERS + str(game_data["player_count"])
    connection.sendall(response.encode("utf-8"))
    connection.close()
    print_server_log(address, request, response)


# makes and saves play move
def make_move(connection, address, request, request_url, params, move):
    try:
        player_id = int(params[0].split("=")[1])
    except IndexError:
        connection.sendall(RESPONSE_BAD_REQUEST.encode("utf-8"))
        connection.close()
        print_server_log(address, request, RESPONSE_BAD_REQUEST)
        return

    file_path = request_url[1:]

    # retrieves play data if existing file exists, otherwise creates a new play data
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

        response = RESPONSE_OK_HEADER + RESPONSE_TEXT_CONTENT_HEADER + RESPONSE_CONTENT_LENGTH_HEADER + "0" \
                   + RESPONSE_END_HEADERS
        connection.sendall(response.encode("utf-8"))
        connection.close()
        print_server_log(address, request, response)

        # if both plays are in it calculates the result and updates game file
        if play_data["moves"][0] is not None and play_data["moves"][1] is not None:
            process_play(file_path, play_data)

    # if player has already made a move for this play it sends a 409 error code
    else:
        connection.sendall(RESPONSE_CONFLICT.encode("utf-8"))
        connection.close()
        print_server_log(address, request, RESPONSE_CONFLICT)


# processes play results and updates play and game files
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
    game_data["finished_plays"] += 1
    with open("game/data.json", "w") as game_file:
        json.dump(game_data, game_file)


# sends file to client given a file path
def send_file(connection, address, request, file_path):
    # if requested file doesn't exist, sends 404 code
    if not os.path.isfile(file_path):
        connection.sendall(RESPONSE_NOT_FOUND.encode("utf-8"))
        connection.close()
        print_server_log(address, request, RESPONSE_NOT_FOUND)
        return

    with open(file_path, "r") as play_file:
        data_file = json.load(play_file)

    body_length = len(json.dumps(data_file).encode("utf-8"))
    response = RESPONSE_OK_HEADER + RESPONSE_JSON_CONTENT_HEADER + RESPONSE_CONTENT_LENGTH_HEADER + str(body_length) \
               + RESPONSE_END_HEADERS + json.dumps(data_file)
    connection.sendall(response.encode("utf-8"))
    connection.close()
    print_server_log(address, request, response)


if __name__ == "__main__":
    main()
