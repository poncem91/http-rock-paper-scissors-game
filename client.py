import sys
import requests


def main():
    game_started = False
    play_thrown = False
    reset_request_sent = False
    play_id = 0

    if len(sys.argv) < 3:
        sys.exit("Missing port number and/or address")
    try:
        server_port = int(sys.argv[2])
    except ValueError:
        sys.exit("Invalid port input")
    server_name = sys.argv[1]

    server_url = "http://" + server_name + ":" + str(server_port)

    print("Welcome to a game of Rock, Paper, Scissors!")
    print("\nCommands:\nR - Rock\nP - Paper\nS - Scissors\nGS - Get overall game score\nPR - Get play "
          "result\nN - Next play\nSTART - Start Game\nRESET - Reset Game\nQ - Quit\n? - Show Commands")
    print("\nEnter START to start a game\n")

    while True:

        input_client = input("\nCommand: ")

        if input_client.upper() == "START":
            # setup game
            if not game_started:
                response = requests.get(server_url + "/game")
                if response.status_code == 200:
                    game_started = True
                    player_id = response.text
                    print("\nBest out of 3 wins the game.")
                    print("\nYou are player #", player_id)
                else:
                    sys.exit("There was an error starting the game. Exiting application...")
            else:
                print("\nYou already have a game in process.")
            continue

        if game_started:
            print("\nYou are on play #", (play_id + 1))

        # quit application
        if input_client.upper() == "Q":
            response = requests.get(server_url + "/game/data.json")
            if response.status_code != 404:
                print("\nYou must first reset the game before quitting.")
                continue
            print("\nBye!")
            sys.exit()

        # prints commands
        elif input_client == "?":
            print("\nCommands:\nR - Rock\nP - Paper\nS - Scissors\nGS - Get overall game score\nPR - Get play "
                  "result\nN - Next play\nSTART - Start Game\nRESET - Reset Game\nQ - Quit\n? - Show Commands")

        elif input_client.upper() == "N":
            if not game_started:
                print("\nPlease start a game first.")
                continue
            if not play_thrown:
                print("\nYou must first make your move for the current play before moving onto the next one")
            else:
                response = requests.get(server_url + "/game/play/" + str(play_id) + ".json")
                play_results = response.json()
                if play_results["done"]:
                    play_thrown = False
                    play_id += 1
                else:
                    print(
                        "\nThe current play is still in progress. Please wait until it's done to go to the next play.")

        # request game score
        elif input_client.upper() == "GS":
            if not game_started:
                print("\nPlease start a game first.")
                continue
            response = requests.get(server_url + "/game/data.json")
            if response.status_code != 200:
                print("Error: Could not retrieve game score.")
                continue
            try:
                player_1_score = response.json()["player_1"]
                player_2_score = response.json()["player_2"]
            except IndexError:
                print("Error: Could not retrieve game score.")
                continue
            print("\nGame Score")
            if player_id == "1":
                print("Your score:", str(player_1_score)[2:-1])
                print("Opponent score:", str(player_2_score)[2:-1])
            else:
                print("Your score:", player_2_score)
                print("Opponent score:", player_1_score)

        # send Rock play
        elif input_client.upper() == "R":
            if not game_started:
                print("\nPlease start a game before making a move.")
                continue
            successful_play = send_play(server_url, play_id, player_id, "R")
            if successful_play:
                play_thrown = True

        # send Paper play
        elif input_client.upper() == "P":
            if not game_started:
                print("\nPlease start a game before making a move.")
                continue
            successful_play = send_play(server_url, play_id, player_id, "P")
            if successful_play:
                play_thrown = True

        # send Scissors play
        elif input_client.upper() == "S":
            if not game_started:
                print("\nPlease start a game before making a move.")
                continue
            successful_play = send_play(server_url, play_id, player_id, "S")
            if successful_play:
                play_thrown = True

        # gets play result
        elif input_client.upper() == "PR":
            if not game_started:
                print("\nPlease start a game first.")
                continue
            if not play_thrown:
                print("\nYou haven't made a move yet. Please make a move first")
                continue

            response = requests.get(server_url + "/game/play/" + str(play_id) + ".json")
            if response.status_code == 404:
                print("\nCould not retrieve play result.")
                continue
            elif response.status_code == 200:
                try:
                    play_results = response.json()
                except:
                    print("\nThere was an error reading the play results file")
                    continue

                player_move = get_play_name(play_results["moves"][int(player_id) - 1])
                opponent_move = get_play_name(play_results["moves"][0 if (int(player_id) - 1) else 1])

                if opponent_move is None:
                    print("\nYour opponent still hasn't made a move. Please try again later.")
                else:
                    player_result = play_results["result"][int(player_id) - 1]

                    print("\nYou threw " + player_move + " and your opponent threw " + opponent_move + "...")
                    if player_result == "W":
                        print("You won!")
                    elif player_result == "L":
                        print("You lost...")
                    elif player_result == "T":
                        print("You tied!")

        elif input_client.upper() == "RESET":
            if not game_started:
                print("\nPlease start a game first.")
                continue
            if reset_request_sent:
                response = requests.delete(server_url + "/game")
                if response.status_code == 200:
                    game_started = False
                    reset_request_sent = False
                    play_thrown = False
                    play_id = 0
                    print("\nThe game has been reset.")
                elif response.status_code == 409:
                    print("\nYour opponent has not requested a game reset.")
                    print("The game can only be reset if both players request a game reset.")
                    print("Please try again later or wait until your opponent has executed a reset.")
                    continue
            else:
                response = requests.patch(server_url + "/game", params={"player": str(player_id), "reset": True})
                if response.status_code == 200:
                    print("\nYour game reset request has been issued.")
                    reset_request_sent = True
                    print("To execute game reset enter the 'RESET' command once again.")
                    continue
                else:
                    print("\nSomething went wrong while attempting to reset the game. Please try again later.")
                    continue

        else:
            print("\nPlease enter a valid command. Enter '?' to see the list of possible commands")


def send_play(url, play_id, player, move):
    response = requests.post(url + "/game/play", params={"id": play_id, "player": player, "move": move})
    if response.status_code == 200:
        if move == "R":
            print("\nYou threw rock!")
        elif move == "S":
            print("\nYou threw scissors!")
        elif move == "P":
            print("\nYou threw paper!")
        return True
    elif response.status_code == 409:
        print("\nYou can't throw duplicate moves on the same play")
        return False


def get_play_name(initial):
    if initial == "R":
        return "rock"
    elif initial == "S":
        return "scissors"
    elif initial == "P":
        return "paper"
    else:
        return None


if __name__ == "__main__":
    main()
