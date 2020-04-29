import random
import logging

module_logger = logging.getLogger()


def set_turn_order(dealer, team1, team2):
    """
    :param dealer: player object who's been chosen as dealer
    :param team1: list with two players (considered the first team). As per Euchre rules,
    sitting opposite from one another
    :param team2: list with two players (considered the first team). As per Euchre rules,
    sitting opposite from one another
    :return: a list of the player order, with the dealer as last:
    """
    table_order = [team1[0], team2[0], team1[1], team2[1]]
    while table_order.index(dealer) != 3:
        # this while statement runs till the dealer is at the end of the list to set the player order.
        shifting = table_order.pop(0)
        table_order.append(shifting)
    return table_order


def get_first_dealer(player_obj_list, deck, card_discard_pile):
    dealer = None
    while not dealer:
        for player in player_obj_list:
            card = deck.pop(0)
            card_discard_pile.append(card)
            if card.d_value == 'Jack' and (card.suit == 'Spades' or card.suit == 'Clubs'):
                dealer = player
                for b_player in player_obj_list:
                    b_player.queue.put(('send_data', 'display_message', '%s got %s and will be the first dealer.' %
                                        (player.name, '%s of %s' % (card.d_value, card.suit))))
                break
            else:
                for c_player in player_obj_list:
                    c_player.queue.put(('send_data', 'display_message', '%s got %s' % (player.name, '%s of %s' %
                                                                                       (card.d_value, card.suit))))
    return dealer, deck, card_discard_pile


def deal(l_deck, l_card_discard_pile, table_order):
    l_deck = l_deck + l_card_discard_pile
    if len(l_deck) != 24:
        raise Exception('Card deck length is not 24!')
    random.shuffle(l_deck)
    module_logger.info('shuffling cards')
    while len(l_deck) > 4:
        for l_player in table_order:
            l_player.hand.append(l_deck.pop(0))
    module_logger.info('cards have been dealt')
    l_card_discard_pile = []
    return l_deck, l_card_discard_pile


if __name__ == '__main__':
    print('Euchre game functions. run server.py')