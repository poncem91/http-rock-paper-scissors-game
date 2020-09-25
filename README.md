# HTTP Server-Client Rock-Paper-Scissors Game

A client-server implementation of the rock paper scissors game implemented in Python where client and server communicate via HTTP messages only.
 
### Client
The client runs on the command line and has a text interface that lets users trigger actions. The client sends appropriate HTTP requests to the server and processes HTTP replies. Client actions include:

* Making a play by sending a message to the server.
* Checking the result of a play and displaying it to the user.
* Checking the score of a game and displaying it to the user.
* Resetting a game.

### Server
The server runs on the command line and accepts HTTP messages from the client and responds with appropriate HTTP status codes. Server actions include:

* Accepting a play message and assure that a player isn't able to make two different throws for the same play.
* Accepting a query for a play result and replying with the result for the specified play.
* Accepting a query for the game score and replying with the score for the specified game.
* Accepting a game reset message that deletes the plays that make up the game. A game should be reset only if both players request a reset.

### Program Invocation
The server process accepts a port parameter on which a clients can connect. For example, `python server.py 5000`
The client process accepts the IP address and the port of the server process. For example, `python client.py 128.111.52.245 5000`
