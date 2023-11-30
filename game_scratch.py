import random

import briscola.game as g
import briscola.deck as d
import random as r

# trick = []
# for i in range(5):
#     card = d.Card(r.choice(d.suits), r.choice(d.ranks))
#     print (card)
#     trick.append(card)
#
# best_card, idx = g.best_card(trick, None)
# print('best card is '+str(best_card))
# print(idx)
#     #g.best_card(trick, 'cups')
# print()
# print()
game = g.Game()
game.start_game()
game.deal_cards()
game.player_bid(0,67)
game.player_bid(3,78)
game.player_bid(2,70)
game.player_bid(1,-1)
game.player_bid(2,-1)
game.player_bid(0,80)
game.player_bid(4,-1)
game.player_bid(3,-1)

print(game.state)
print(game.bid_winner.id)
partner_card = d.Card(random.choice(d.suits), random.choice(d.ranks))
print('partner_card: ' + str(partner_card))

game.call_partner_rank(partner_card.rank)
for i in range(5):
    game._next_player_play_random_card()


game.call_partner_suit(partner_card.suit)

for i in range(5):
    game._next_player_play_random_card()