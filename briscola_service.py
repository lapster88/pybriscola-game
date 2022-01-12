import asyncio
import time

import websockets as ws
from briscola.game import Game

async def consumer_handler(websocket):
    async for message in websocket:
        time.sleep(1)
        reply = consumer(message)
        await websocket.send(reply)

def consumer(message):
    print(message)
    reply = 'ping'
    return reply

async def main():
    async with ws.connect('ws://localhost:8000/ws/gameservice/') as websocket:
        await consumer_handler(websocket)
        #await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())


