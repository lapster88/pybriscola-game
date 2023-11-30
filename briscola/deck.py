import random as r
suits = ['cups', 'coins', 'swords', 'clubs']
ranks = range(1, 11)
values = [0, 0, 0, 0, 0, 2, 3, 4, 10, 11]

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.value = values[rank-1]

    def __str__(self):
        return str(self.suit) + ',' + str(self.rank)

    def __eq__(self, other):
        return (self.suit == other.suit) and (self.rank == other.rank)

class Deck:
    def __init__(self):
        self.cards = []
        for suit in suits:
            for rank in ranks:
                self.cards.append(Card(suit, rank))

    def __str__(self):
        cards_str = []
        for card in self.cards:
            cards_str.append(str(card))

        return str(cards_str)

    def shuffle(self):
        r.shuffle(self.cards)

    def deal_hands(self):
        self.shuffle()

        return [self.cards[i:i + 8] for i in range(0, len(self.cards), 8)]

