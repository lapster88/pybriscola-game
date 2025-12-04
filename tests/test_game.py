from unittest import TestCase

import briscola.deck as deck
from briscola.game import Game


class TestGame(TestCase):
    def test_bidding_complete(self):
        g = Game()
        g.start_game()
        g.deal_cards()
        self.assertFalse(g.bidding_complete())

        for player in g.players:
            player.bid = -1

        self.assertFalse(g.bidding_complete())

        g.player_bid(0, 67)

        self.assertTrue(g.bidding_complete())

    def test_start_game(self):
        g = Game()
        g.start_game()
        self.assertEqual(g.state, 'ready')

    def test_deal_cards(self):
        g= Game()
        g.start_game()
        g.deal_cards()
        for player in g.players:
            self.assertEqual(len(player.hand), 8)
            self.assertEqual(len(player.original_hand), 8)
            self.assertTrue(sum([card.value for card in player.hand]) >= g.minimum_hand_value)

        self.assertEqual(g.state, 'bid')

    def test_player_bid(self):
        g = Game()
        g.start_game()
        g.deal_cards()
        state, winner_id, winning_bid = g.player_bid(0, 70)
        self.assertEqual(state, 'bid')
        self.assertEqual(winner_id, 0)
        self.assertEqual(winning_bid, 70)
        # four passes advance to call-partner-rank
        for pid in [1, 2, 3, 4]:
            state, winner_id, winning_bid = g.player_bid(pid, -1)
        self.assertEqual(state, 'call-partner-rank')
        self.assertEqual(g.current_player_id, winner_id)

    def test_call_partner_rank(self):
        g = Game()
        g.start_game()
        g.deal_cards()
        # finish bidding to advance state
        g.player_bid(0, 70)
        for pid in [1, 2, 3, 4]:
            g.player_bid(pid, -1)
        self.assertEqual(g.state, 'call-partner-rank')
        state, partner_rank = g.call_partner_rank(7)
        self.assertEqual(state, 'play-first-trick')
        self.assertEqual(partner_rank, 7)

    def test_call_partner_suit(self):
        g = Game()
        g.start_game()
        # build deterministic hands/original hands
        ace_coins = deck.Card('coins', 1)
        three_swords = deck.Card('swords', 3)
        seven_cups = deck.Card('cups', 7)
        four_clubs = deck.Card('clubs', 4)
        king_coins = deck.Card('coins', 10)
        g.state = 'call-partner-suit'
        g.partner_rank = ace_coins.rank
        g.players[2].original_hand = [ace_coins]
        g.players[0].original_hand = [three_swords]
        g.players[1].original_hand = [seven_cups]
        g.players[3].original_hand = [four_clubs]
        g.players[4].original_hand = [king_coins]
        # set a completed trick
        g.current_trick = [
            (three_swords, 0),
            (seven_cups, 1),
            (ace_coins, 2),
            (four_clubs, 3),
            (king_coins, 4),
        ]
        state, suit, found_id = g.call_partner_suit('coins')
        self.assertEqual(state, 'trick-won')
        self.assertEqual(suit, 'coins')
        self.assertEqual(found_id, 2)
        # king of coins wins the trick
        self.assertEqual(g.current_leader_id, 4)
        self.assertEqual(g.current_player_id, 4)
        self.assertEqual(g.current_trick, [])
        self.assertGreater(g.players[4].points, 0)

    def test_end_trick(self):
        g = Game()
        g.start_game()
        g.state = 'play-tricks'
        card = deck.Card('coins', 3)
        g.players[0].hand = [card]
        g.current_trick = [(card, 0)]
        g.end_trick(card, 0)
        self.assertEqual(g.current_trick, [])
        self.assertEqual(g.current_player_id, 0)
        self.assertEqual(g.current_leader_id, 0)
        self.assertGreaterEqual(g.players[0].points, card.value)

    def test_play_card(self):
        g = Game()
        g.start_game()
        g.state = 'play-tricks'
        g.current_player_id = 0
        card0 = deck.Card('coins', 7)
        g.players[0].hand = [card0]
        state, winning_card, winning_player = g.play_card(0, card0)
        self.assertEqual(state, 'play-tricks')
        self.assertIn((card0, 0), g.current_trick)
        self.assertNotIn(card0, g.players[0].hand)
        self.assertEqual(g.current_player_id, 1)
        # play 5th card in first trick should advance to call-partner-suit
        g = Game()
        g.start_game()
        g.state = 'play-first-trick'
        g.partner_rank = 1
        g.partner_suit = None
        g.current_trick = [(deck.Card('coins', 2), i) for i in range(4)]
        g.players[4].hand = [deck.Card('coins', 3)]
        g.current_player_id = 4
        state, _, _ = g.play_card(4, g.players[4].hand[0])
        self.assertEqual(state, 'call-partner-suit')

    def test__next_player_play_random_card(self):
        g = Game()
        g.start_game()
        g.deal_cards()
        g.state = 'play-tricks'
        g.current_player_id = 0
        g._next_player_play_random_card()
        self.assertEqual(len(g.current_trick), 1)

    def test__inc_current_player(self):
        g = Game()
        g.current_player_id = 4
        g._inc_current_player()
        self.assertEqual(g.current_player_id, 0)
