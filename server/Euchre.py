import random
import logging
import threading
from queue import Queue

module_logger = logging.getLogger()


def deal(l_deck, l_card_discard_pile, l_player_object_list):
    """
    deal combines the passed deck and discard pile arrays, randomizes them, and deals out the cards appropriately
    :param l_deck: list of cards in the deck
    :param l_card_discard_pile: list of discarded cards
    :param l_player_object_list: list of player objects
    :return:
    """
    l_deck = l_deck + l_card_discard_pile
    for l_player in l_player_object_list:
        if len(l_player.hand) > 0:
            l_deck.append(l_player.hand)
            l_player.hand = []
    if len(l_deck) != 24:
        raise Exception('Card deck length is not 24!')
    random.shuffle(l_deck)
    module_logger.info('shuffling cards')
    while len(l_deck) > 4:
        for l_player in l_player_object_list:
            l_player.hand.append(l_deck.pop(0))
    module_logger.info('cards have been dealt')
    l_card_discard_pile = []
    return l_deck, l_card_discard_pile


class Euchre:
    def __init__(self):
        self.dealer = ''
        self.trump = ''
        self.queue = Queue()
        self.player_order = []
        self.team1 = []
        self.team2 = []
        self._round_turn_order = []
        self._discard_list = []  # meant for temporarily pushing in cards

    def dealer_pick_up_card(self, trump_card, first_trump_str):
        while True:
            dealer_str = 'Which card do you want to replace with %s [enter the number]: \n' % first_trump_str + \
                         '\n'.join(['[%d] ' % (self.dealer.hand.index(x)) + x.d_value + ' of ' +
                                    x.suit for x in self.dealer.hand])
            self.dealer.queue.put(['send_data', 'require_input', dealer_str])
            dealer_resp = self.queue.get()
            if dealer_resp in range(0, 5):
                l_discard = self.dealer.hand.pop(dealer_resp)
                self.hand.append(trump_card)
                break
            else:
                continue

        self._discard_list.append(l_discard)

    def set_turn_order(self):
        """
        sets the turn order given the current dealer and two team lists
        """
        _table_order = [self.team1[0], self.team2[0], self.team1[1], self.team2[1]]
        while _table_order.index(self.dealer) != 3:
            # this while statement runs till the dealer is at the end of the list to set the player order.
            shifting = _table_order.pop(0)
            _table_order.append(shifting)
        self.player_order = _table_order

    def pick_trump(self, kitty):
        discard_pile = []
        trump_card = kitty.pop(0)
        discard_pile += kitty
        first_trump_str = '%s of %s' % (trump_card.d_value, trump_card.suit)
        for l_player in self.player_order:
            l_player.queue.put(['send_data', 'display_message', '%s is up for trump. %s chooses first.' %
                               (first_trump_str, self.player_order[0].name)])
        trump_selected = False
        for l_player in self.player_order:
            while True:
                if self.player_order.index(l_player) != 3:
                    l_player.queue.put(['send_data', 'require_input',
                                        'Have dealer pickup the card, making %s trump or pass? [1 = pickup, 2 = pass] ' %
                                       trump_card.suit])
                else:
                    l_player.queue.put(['send_data', 'require_input',
                                        'Do you want to pickup the card, making %s trump or pass ? [1 = pickup, 2 = pass] '
                                        % trump_card.suit])
                trump_response = self.queue.get()
                if trump_response == '1':
                    self.trump = trump_card.suit
                    trump_selected = True
                    if self.player_order.index(l_player) != 3:
                        dealer_thread = threading.Thread(target=self.dealer_pick_up_card,
                                                         args=(trump_card, first_trump_str))
                        player_thread = threading.Thread(self.go_alone)
                        threads = [dealer_thread, player_thread]
                        dealer_thread.start()
                        player_thread.start()
                        for thread in threads:
                            thread.join()
                        module_logger.debug('Completed dealer/player threads when picking trump.')
                    else:
                        self.dealer_pick_up_card()
                        self.go_alone()
                elif trump_response == '2':
                    break
                else:
                    continue

            if trump_selected:
                # doesn't account for no one picking trump
                break
        discard_pile += self._discard_list
        self._discard_list = []
        return discard_pile

    def get_first_dealer(self, deck, card_discard_pile):
        """
        first black jack deals. Euchre.player_order must already be set
        :param deck: list of all cards
        :param card_discard_pile:
        :return:
        """
        dealer = None
        if len(deck) != 24:
            raise Exception('deck is contains more or less than 24 cards')
        while not dealer:
            for player in self.player_order:
                card = deck.pop(0)
                card_discard_pile.append(card)
                if card.d_value == 'Jack' and (card.suit == 'Spades' or card.suit == 'Clubs'):
                    dealer = player
                    for b_player in self.player_order:
                        b_player.queue.put(['send_data', 'display_message', '%s got %s and will be the first dealer.' %
                                            (player.name, '%s of %s' % (card.d_value, card.suit))])
                        b_player.queue.put(['send_line_separator'])
                    break
                else:
                    for c_player in self.player_order:
                        c_player.queue.put(['send_data', 'display_message', '%s got %s' % (player.name, '%s of %s' %
                                                                                           (card.d_value, card.suit))])
        self.dealer = dealer
        return deck, card_discard_pile

    def go_alone(self, current_player):
        while True:
            current_player.queue.put(['send_data', 'require_input',
                                      'Do you wish to play alone this round? [1 = no, 2 = yes] '])
            go_alone_response = self.queue.get()
            if go_alone_response == 1:
                self._round_turn_order = self.player_order
                break
            elif go_alone_response == 2:
                self._round_turn_order = self.player_order
                player_index = self._round_turn_order.index(current_player)
                try:
                    team_mate_index = self._round_turn_order.index(player_index + 2)

                except ValueError:
                    team_mate_index = self._round_turn_order.index(player_index - 2)
                finally:
                    self._round_turn_order.pop(team_mate_index)
                    break
            else:
                continue
        return


if __name__ == '__main__':
    print('Euchre game functions. run server.py')