import copy
import random

import briscola.player as p
import briscola.deck as d

# Helper functions

def trick_winner(trick, trump_suit):
    '''
    Determines the best card in cards based on the trump_suit. first card in the list is the secondary trump
    :param trick:
    :param trump_suit: suit that can trump any other suit
    :return: Card object representing the best card in cards.
    '''

    # first card is winning unless we find a higher card in that suit or a trump suit card
    cards = list(list(zip(*trick))[0])
    winning_card = cards[0]
    winning_card_idx = 0
    for idx, card in enumerate(cards):
        # found a trump card
        if card.suit == trump_suit:

            # winning card is also trump card
            if winning_card.suit == trump_suit:

                # assign winning card by rank
                if card.rank > winning_card.rank:
                    winning_card = card
                    winning_card_idx = idx

            # winning card is not a trump card, replace it
            else:
                winning_card = card
                winning_card_idx = idx

        #found a card matching winning card suit
        elif card.suit == winning_card.suit:

            #assign winning card by rank
            if card.rank > winning_card.rank:
                winning_card = card
                winning_card_idx = idx

    return winning_card, winning_card_idx


class Game:
    def __init__(self):
        self.state = 'idle'
        self.bid = 60
        self.bid_winner = None
        self.partner = None
        self.players = [p.Player(i) for i in range(5)]
        self.deck = d.Deck()
        self.partner_rank = None
        self.partner_suit = None
        self.current_trick = []
        self.current_leader_id = None
        self.current_player_id = None

        pass

    def bidding_complete(self):
        '''
        Check to see if bidding is complete
        :return: True if bidding is  complete, False if it isn't
        '''

        # reset number of passed players
        pass_count = 0

        for player in self.players:
            # increment count if player has "passed" by bidding -1
            if player.bid == -1:
                pass_count += 1

        # if four players have passed bidding is complete
        return pass_count >= 4

# Game Modifiers
    def start_game(self):
        """
        Sets game to the ready state, takes care of any setup actions
        :return: game state
        """
        self.state = 'ready'
        return self.state

    def deal_cards(self):
        '''
        Shuffles the deck and deals out five hands of eight
        :return: returns game state
        '''

        if self.state != 'ready':
            raise GameStateError('ready', self.state)

        hands = self.deck.deal_hands()

        for hand, player in list(zip(hands, self.players)):
            player.hand = hand
            player.original_hand = copy.deepcopy(hand)
            # TODO: send hand information to each client

        self.state = 'bid'

        return self.state, hands

    def player_bid(self, player_id, amount):
        """Update game state with a player's bid.

        player_id - id of the bidding player
        amount - the amount the player is bidding
        """
        if player_id > 4 or player_id < 0:
            raise ValueError('player_id must be 0-4')
        if amount != -1 and (amount < 61 or amount > 120):
            raise ValueError('amount must be 61-120')

        if self.state != 'bid':
            raise GameStateError('bid', self.state)

        player = self.players[player_id]
        player.bid = amount

        if amount > self.bid:
            self.bid = amount
            self.bid_winner = player

        if self.bidding_complete():
            self.current_leader_id = self.bid_winner.id
            self.current_player_id = self.bid_winner.id
            self.state = "call-partner-rank"

        return self.state, self.bid_winner.id, self.bid

    def call_partner_rank(self, rank):
        if rank not in d.ranks:
            raise ValueError('rank must be 1-10')

        if self.state != 'call-partner-rank':
            raise GameStateError('call-partner-rank', self.state)


        self.partner_rank = rank
        self.state = 'play-first-hand'

        return self.state, self.partner_rank

    def call_partner_suit(self, suit):
        if suit not in d.suits:
            raise ValueError('suit must be one of' + str(d.suits))

        if self.state != 'call-partner-suit':
            raise GameStateError('call-partner-suit', self.state)

        # record partner suit
        self.partner_suit = suit

        # record partner card
        partner_card = d.Card(self.partner_suit, self.partner_rank)

        # search for partner
        for player in self.players:
            for card in player.original_hand:
                if card == partner_card:
                    self.partner = player
                    break
            if self.partner is not None:
                break
        if self.partner is None:
            raise ValueError('partner card not found')

        print('partner is player ' + str(self.partner.id))

        self.state = 'play-hands'

        return self.state, self.partner_suit, self.partner.id

    def play_card(self, player_id, card):
        self.players[player_id].hand.remove(card)

        self.current_trick.append((card, player_id))

        self.current_player_id += 1
        if self.current_player_id > 4:
            self.current_player_id = 0

        # TODO: announce the card played

        if len(self.current_trick) == 5:
            winning_card, winning_card_idx = trick_winner(self.current_trick, self.partner_suit)
            # find the winning player by going "around the table" from the leader to the idx of the winning card
            winning_player_idx = self.current_trick[winning_card_idx][1]
            print('winner is '+str(winning_card) + ' played by ' +str(winning_player_idx))

            # give winning player trick and update their points
            winning_player = self.players[winning_player_idx]
            winning_player.tricks_won.append(self.current_trick)
            winning_player.points += sum([card.value for card, player_id in self.current_trick])

            # reset state for next trick
            #print(self.current_trick)
            self.current_trick = []
            self.current_leader_id = winning_player_idx
            self.current_player_id = winning_player_idx

            if self.state == 'play-first-hand':
                self.state = 'call-partner-suit'

            # TODO: announce trick winner and next leader
    def _next_player_play_random_card(self):
        card_idx = random.randint(0,4)
        player = self.players[self.current_player_id]
        print(str(player.id) + ' played ' + str(player.hand[card_idx]))
        self.play_card(self.current_player_id, player.hand[card_idx])


class GameStateError(Exception):
    def __init__(self, expected_state, actual_state):
        self.message = "State is {}, expected {}".format(expected_state, actual_state)
        super().__init__(self.message)
