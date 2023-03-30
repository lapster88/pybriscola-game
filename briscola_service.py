import asyncio
import json
import random
import string
import time
from threading import Thread

import gevent
import websockets as ws
from briscola.game import Game
from briscola.game_server import GameServer

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

class BriscolaService:

    def __init__(self):
        self.games = {}
        self.game_tasks = {}
        #self.current_id = 1000
        self.group = asyncio.sleep(1)

    async def consumer_handler(self, websocket):
        """Async websocket message handler"""
        async for message in websocket:
            time.sleep(1)
            reply = self.consumer(message)
            await websocket.send(reply)

    def consumer(self, message):
        """Synchronous message handler"""
        print(message)
        message_json = json.loads(message)
        reply = ''
        if message_json['message_type'] == 'create':
            game_id = id_generator()
            while game_id in self.games.keys():
                game_id = id_generator()

            print(game_id)
            new_game = GameServer(game_id)
            self.games[game_id] = new_game
            self.game_tasks[game_id] = asyncio.create_task(new_game.main())
            reply = json.dumps(
                {
                    'message_type' : 'create',
                    'result' : 'success',
                    'game_id' : game_id
                }
            )
        return reply

    async def main(self):
        # Setup websocket connection
        async with ws.connect('ws://localhost:8000/ws/gameservice/') as websocket:
            #  Call websocket message handler
            await self.consumer_handler(websocket)

if __name__ == "__main__":
    asyncio.run(BriscolaService().main())


