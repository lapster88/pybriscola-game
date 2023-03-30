import asyncio
import json
import time

import zmq
import websockets as ws
from briscola.game import Game

SERVER_NAME = 'tcp://localhost:'

class GameServer():
    def __init__(self, game_id):
        self.game_id = game_id
        self.game = Game()

    async def consumer_handler(self, websocket):
        async for message in websocket:
            await asyncio.sleep(1)
            reply = self.consumer(message)
            await websocket.send(reply)

    def consumer(self, message):
        print(message)
        reply = 'ping'
        return reply

    async def main(self):
        async with ws.connect('ws://localhost:8000/ws/gameserver/') as websocket:
            message = {
                'message_type' : 'created',
                'game_id' : self.game_id
            }
            websocket.send(json.dumps(message))
            await self.consumer_handler(websocket)



