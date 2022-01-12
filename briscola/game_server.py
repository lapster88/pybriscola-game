import zmq

from briscola.game import Game

SERVER_NAME = 'tcp://localhost:'

class GameServer():
    def __init__(self, router_port, pub_port):
        self.game = Game()
        context = zmq.Context.instance()
        self.client_router = context.socket(zmq.ROUTER)
        self.client_router.bind(SERVER_NAME + str(router_port))
        self.client_pub = context.socket(zmq.PUB)
        self.client_pub.bind(SERVER_NAME + str(pub_port))

    def start(self):
        #reset/set inital Game state
        while True:
            #recv from router
            request = self.client_router.recv_json()

            #determine type of request received and ack it

            reply = {}
            self.client_router.send_json(reply)

            # update game state
            game_update = {}
            #publish new game state
            self.client_pub.send_json(game_update)



