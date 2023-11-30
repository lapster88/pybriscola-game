from unittest import TestCase
import briscola.deck as d

class TestCard(TestCase):
    def test_eq(self):
        card = d.Card('cups', 1)
        card2 = d.Card('cups', 1)
        self.assertEqual(card, card2)
    def test_neq_suit(self):
        card = d.Card('cups', 1)
        card2 = d.Card('coins', 2)
        self.assertNotEqual(card, card2)

    def test_neq_rank(self):
        card = d.Card('cups', 1)
        card2 = d.Card('cups', 2)
        self.assertNotEqual(card, card2)


class TestDeck(TestCase):

    def test_shuffle(self):
        deck = d.Deck()
        deck.shuffle()
        self.assertNotEqual(str(deck), str(d.Deck()))
