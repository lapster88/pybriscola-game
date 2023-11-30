
class Player:
    def __init__(self, id):
        self.id = id
        self.original_hand = []
        self.hand = []
        self.bid = 0
        self.tricks_won = []
        self.points = 0
