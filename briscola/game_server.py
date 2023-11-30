import asyncio
import json
import time

import zmq
import websockets as ws
from briscola.game import Game

SERVER_NAME = 'tcp://localhost:'

class GameServer():
    '''
    this class is responsible for managing a single game
    '''
    def __init__(self, game_id):
        self.game_id = game_id
        self.game = Game()

    async def consumer_handler(self, websocket):
        async for message in websocket:
            await asyncio.sleep(1)
            reply = self.consumer(message)
            await websocket.send(reply)

    def consumer(self, message):

        if message['message_type'] == 'bid':
            player_id = message['player_id']
            bid = message['bid']
            state, winner_id, winning_bid = self.game.player_bid(player_id, bid)
            if state == 'bid':
                reply = json.dumps(
                    {
                        'message_type': 'bid',
                        'result': 'success',
                        'player_id': player_id,
                        'bid': bid,
                        'winner_id': winner_id,
                        'winning_bid': winning_bid
                    }
                )
            elif state == 'call-partner-rank':
                reply = json.dumps(
                    {
                        'message_type' : 'bidding_complete',
                        'result' : 'success',
                        'player_id': player_id,
                        'bid': bid,
                        'winner_id' : winner_id,
                        'winning_bid' : winning_bid
                    }
                )

        elif message['message-type'] == 'call-partner-rank':
            player_id = message['player_id']
            partner_rank = message['partner_rank']
            state, partner_rank = self.game.call_partner_rank(partner_rank)
            reply = json.dumps(
                {
                    'message_type': 'call-partner-rank',
                    'result': 'success',
                    'player_id': player_id,
                    'partner_rank': partner_rank,
                }
            )

        elif message['message-type'] == 'call-partner-suit':
            player_id = message['player_id']
            partner_suit = message['partner_suit']
            state, partner_suit, partner_id = self.game.call_partner_suit(partner_suit)
            reply = json.dumps(
                {
                    'message_type': 'call-partner-suit',
                    'result': 'success',
                    'player_id': player_id,
                    'partner_rank': partner_suit,
                    'partner_id' : partner_id
                }
            )

        else:
            reply = '{"message_type":"error","result":"error"}'
        print(message)
        return reply

    async def main(self):
        async with ws.connect('ws://localhost:8000/ws/gameserver/') as websocket:
            message = {
                'message_type' : 'created',
                'game_id' : self.game_id
            }
            websocket.send(json.dumps(message))
            await self.consumer_handler(websocket)



