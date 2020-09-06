import socket
import sys


def main():
    game_started = False
    play_thrown = False
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

    print("Welcome to a game of Rock, Paper, Scissors!")
    print("\nBest out of 3 wins the game.")
    print("\nCommands:\nR - Rock\nP - Paper\nS - Scissors\nGS - Get overall game score\nPR - Get play "
          "result\nN - Next play\nRESET - Reset Game\nQ - Quit\n? - Show Commands")

    while True:
        http_response = ""

        # setup game
        if not game_started:
            client_socket.sendall(get_request("/start-game", server_name).encode("utf-8"))
            http_response = client_socket.recv(1024).decode("utf-8")
            response_list = http_response.split()
            response_status = response_list[1]
            if response_status == "200":
                game_started = True
                player_id = response_list[5]
                print("\nYou are player #", player_id)
            else:
                print("\nThere was an error starting the game")
                break

        input_client = input("\nCommand: ")

        # quit application
        if input_client.upper() == "Q":
            client_socket.sendall(get_request("/quit-game", server_name).encode("utf-8"))
            break

        # prints commands
        elif input_client == "?":
            print("\nCommands:\nR - Rock\nP - Paper\nS - Scissors\nGS - Get overall game score\nPR - Get play "
                  "result\nN - Next play\nRESET - Reset Game\nQ - Quit\n? - Show Commands")

        elif input_client.upper() == "N":
            if not play_thrown:
                print("You must first make your move for the current play before moving onto the next one")
            else:
                play_thrown = False
                play_count += 1

        # request game score
        elif input_client.upper() == "GS":
            client_socket.sendall((get_request("/gamescore", server_name).encode("utf-8")))
            http_response = client_socket.recv(1024).decode("utf-8")
            response_list = http_response.split()
            response_status = response_list[1]
            if response_status != "200":
                print("Error: Could not retrieve game score. Exiting game.")
                break
            try:
                player_1_score = response_list[5]
                player_2_score = response_list[6]
            except IndexError:
                print("Error: Could not retrieve game score. Exiting game.")
                break
            print("\nGame Score - WINS-LOSES-TIES")
            if player_id == "1":
                print("Your score:", player_1_score)
                print("Opponent score:", player_2_score)
            else:
                print("Your score:", player_2_score)
                print("Opponent score:", player_1_score)

        # send Rock play
        elif input_client.upper() == "R":
            successful_play = send_play("R", server_name, player_id, client_socket, play_count)
            if successful_play:
                play_thrown = True

        # send Paper play
        elif input_client.upper() == "P":
            successful_play = send_play("P", server_name, player_id, client_socket, play_count)
            if successful_play:
                play_thrown = True

        # send Scissors play
        elif input_client.upper() == "S":
            successful_play = send_play("S", server_name, player_id, client_socket, play_count)
            if successful_play:
                play_thrown = True

        # gets play result
        elif input_client.upper() == "PR":
            if not play_thrown:
                print("You haven't made a move yet. Please make a move first")
            else:
                url = "/play?id=" + str(play_count)
                client_socket.sendall(get_request(url, server_name).encode("utf-8"))
                print("\nPlease wait...\n")
                http_response = client_socket.recv(1024).decode("utf-8")
                response_list = http_response.split()
                try:
                    response_body = response_list[5]
                except IndexError:
                    print("Error: Could not retrieve play result. Exiting game.")
                    break
                results = response_body.split("-")
                player_result = results[int(player_id) - 1]
                if player_result == "W":
                    print("You won!")
                elif player_result == "L":
                    print("You lost...")
                elif player_result == "T":
                    print("You tied!")

        else:
            print("\nPlease enter a valid command. Enter '?' to see the list of possible commands")

    client_socket.close()


def get_request(url, server):
    return "GET " + url + " HTTP/1.1\r\nHost: " + server + "\r\nAccept: text/html\r\n\r\n"


def post_request(url, server, player, move, p_id):
    return "POST " + url + " HTTP/1.1\r\nHost: " + server + "\r\nContent-Type: text/html\r\n\r\nplayer=" + player + "&move=" + move + "&id=" + str(p_id)


def send_play(play, server, player, c_socket, play_id):
    c_socket.sendall(post_request("/play", server, player, play, play_id).encode("utf-8"))
    http_response = c_socket.recv(1024).decode("utf-8")
    response_list = http_response.split()
    response_status = response_list[1]
    if response_status == "200":
        if play == "R":
            print("\nYou threw rock!")
        elif play == "S":
            print("\nYou threw scissors!")
        elif play == "P":
            print("\nYou threw paper!")
        return True
    elif response_status == "409":
        print("\nYou can't throw duplicate moves on the same play")
        return False


if __name__ == "__main__":
    main()
