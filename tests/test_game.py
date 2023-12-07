from unittest import TestCase

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
        self.fail()

    def test_call_partner_rank(self):
        self.fail()

    def test_call_partner_suit(self):
        self.fail()

    def test_end_trick(self):
        self.fail()

    def test_play_card(self):
        self.fail()

    def test__next_player_play_random_card(self):
        self.fail()

    def test__inc_current_player(self):
        self.fail()
