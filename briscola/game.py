import player as p


class Game:
    def __init__(self):
        self.state = 'idle'
        self.bid = 60
        self.bid_winner = -1
        self.players = [p.Player(i) for i in range(5)]

        pass

    def player_bid(self, player_id, amount):
        """Update game state with a player's bid.

        player_id - id of the bidding player
        amount - the amount the player is bidding
        """
        if self.state == 'bid':
            pass
        else:
            raise GameStateError('bid', self.state)
        pass


class GameStateError(Exception):
    def __init__(self, expected_state, actual_state):
        self.message = "State is {}, expected {}".format(expected_state, actual_state)
        super().__init__(self.message)