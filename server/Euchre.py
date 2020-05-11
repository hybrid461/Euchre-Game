import random
import logging
import time
import Cards

module_logger = logging.getLogger()

class Euchre:
    def __init__(self):
        self.dealer = ''
        self.trump = ''
        self.player_order = []
        self.team1 = []
        self.team2 = []
        self.deck = Cards.build_deck()
        self.card_discard_pile = []
        self._round_off_team = None
        self._round_def_team = None
        self._round_turn_order = []
        self._round_kitty = []

    def start_game(self):
        random.shuffle(self.deck)
        self.get_first_dealer()

    def get_first_dealer(self):
        """
        first black jack deals. Euchre.player_order must already be set
        :param deck: list of all cards
        :param card_discard_pile:
        :return:
        """
        dealer = None
        if len(self.deck) != 24:
            raise Exception('deck is contains more or less than 24 cards')
        for l_player in self.player_order:
            l_player.queue_in.put(['display_message', 'Choosing the dealer, first Black Jack deals!'])
        time.sleep(2)
        while not dealer:
            for player in self.player_order:
                card = self.deck.pop(0)
                self.card_discard_pile.append(card)
                if card.d_value == 'Jack' and (card.suit == 'Spades' or card.suit == 'Clubs'):
                    dealer = player
                    for b_player in self.player_order:
                        b_player.queue_in.put(['display_message', '%s got %s and will be the first dealer.' %
                                            (player.name, '%s of %s' % (card.d_value, card.suit))])
                        b_player.queue_in.put(['send_line_separator'])
                    break
                else:
                    for c_player in self.player_order:
                        c_player.queue_in.put(['display_message', '%s got %s' % (player.name, '%s of %s' %
                                                                                           (card.d_value, card.suit))])
        self.dealer = dealer
        module_logger.info('Dealer is: ' + self.dealer.name)

    def start_round(self):
        self.set_player_order()
        self.deal()
        self.show_all_players_their_hands()
        trump_chooser = self.pick_trump()
        if not trump_chooser:
            # onto next dealer
            pass
        else:
            self._setup_round_teams(trump_chooser)  # must run before adjust_round_order
            self.go_alone(trump_chooser)
            self.adjust_round_order()

    def deal(self):
        l_deck = self.deck + self.card_discard_pile
        for l_player in self.player_order:
            if len(l_player.hand) > 0:
                l_deck.append(l_player.hand)
                l_player.hand = []
        if len(l_deck) != 24:
            raise Exception('Card deck length is not 24!')
        random.shuffle(l_deck)
        module_logger.info('shuffling cards')
        while len(l_deck) > 4:
            for l_player in self.player_order:
                l_player.hand.append(l_deck.pop(0))
        module_logger.info('cards have been dealt')
        self.card_discard_pile = []
        self.deck = []
        self._round_kitty = l_deck

    def show_all_players_their_hands(self):
        for l_player in self.player_order:
            l_player.display_hand()

    def set_player_order(self):
        """
        sets the player order given the current dealer and two team lists
        """
        module_logger.info('Current player order: ' + ','.join([x.name for x in self.player_order]))
        while self.player_order.index(self.dealer) != 3:
            # this while statement runs till the dealer is at the end of the list to set the player order.
            shifting = self.player_order.pop(0)
            self.player_order.append(shifting)
        module_logger.info('Updated player order: ' + ','.join([x.name for x in self.player_order]))

    def pick_trump(self):
        trump_card = self._round_kitty.pop(0)
        self.card_discard_pile += self._round_kitty
        first_trump_str = '%s of %s' % (trump_card.d_value, trump_card.suit)
        for l_player in self.player_order:
            l_player.queue_in.put(['display_message', '%s is up for trump. %s chooses first.' %
                               (first_trump_str, self.player_order[0].name)])
        trump_selected = False
        trump_chooser = None
        for l_player in self.player_order:
            if trump_selected:
                break
            while True:
                if self.player_order.index(l_player) != 3:
                    l_player.queue_in.put(['require_input',
                                        'Have dealer pickup the card, making %s trump or pass? [1 = pickup, 2 = pass] ' %
                                       trump_card.suit])
                else:
                    l_player.queue_in.put(['require_input',
                                        'Do you want to pickup the card, making %s trump or pass ? [1 = pickup, 2 = pass] '
                                        % trump_card.suit])
                trump_response = l_player.queue_out.get()
                if trump_response == '1':
                    self.trump = trump_card.suit
                    self.dealer_pick_up_card(trump_card, first_trump_str)
                    trump_selected = True
                    trump_chooser = l_player
                    for x_player in self.player_order:
                        x_player.queue_in.put(['display_message', '%s has chosen %s as trump for this round' %
                                               (l_player.name, self.trump)])
                        x_player.queue_in.put(['send_line_separator'])
                    break
                elif trump_response == '2':
                    for x_player in self.player_order:
                        x_player.queue_in.put(['display_message', '%s has passed.' % l_player.name])
                    break
                else:
                    continue
        if not trump_selected:
            pass
            # need to choose a diff suit for trump
        return trump_chooser

    def dealer_pick_up_card(self, trump_card, first_trump_str):
        while True:
            dealer_str = 'Which card do you want to replace with %s [enter the number]: \n' % first_trump_str + \
                         '\n'.join(['[%d] ' % (self.dealer.hand.index(x)) + x.d_value + ' of ' +
                                    x.suit for x in self.dealer.hand]) + '\n'
            self.dealer.queue_in.put(['require_input', dealer_str])
            dealer_resp = int(self.dealer.queue_out.get())
            if dealer_resp in range(0, 5):
                self.card_discard_pile.append(self.dealer.hand.pop(dealer_resp))
                self.dealer.hand.append(trump_card)
                self.dealer.display_hand()
                break
            else:
                continue

    def go_alone(self, trump_chooser):
        trump_chooser_index = self._round_off_team.index(trump_chooser)
        if trump_chooser_index == 0:
            off_teammate_index = 1
        else:
            off_teammate_index = 0
        off_teammate = self._round_off_team[off_teammate_index]
        o_alone_player = self.go_alone_question([trump_chooser, off_teammate])
        if o_alone_player:
            self._round_off_team = [o_alone_player]
            for x_player in self.player_order:
                x_player.queue_in.put(['display_message', '%s has chosen to go alone' % x_player.name])
        d_alone_player = self.go_alone_question(self._round_def_team)
        if d_alone_player:
            self._round_def_team = [d_alone_player]
            for x_player in self.player_order:
                x_player.queue_in.put(['display_message', '%s has chosen to go alone' % x_player.name])

    def go_alone_question(self, team_list):
        for l_player in team_list:
            l_player.queue_in.put(['require_input', 'Do you wish to play alone this round? [1 = no, 2 = yes] '])
            go_alone_response = l_player.queue_out.get()
            if go_alone_response == '1':
                module_logger.info('%s chose to not go alone' % l_player.name)
                continue
            elif go_alone_response == '2':
                return l_player

    def _setup_round_teams(self, trump_chooser):
        if trump_chooser in self.team1:
            self._round_off_team = self.team1
            self._round_def_team = self.team2
        else:
            self._round_off_team = self.team2
            self._round_def_team = self.team1

    def adjust_round_order(self):
        for l_player in self.player_order:
            if l_player in self._round_off_team:
                self._round_turn_order.append(l_player)
            elif l_player in self._round_def_team:
                self._round_turn_order.append(l_player)
        module_logger.info('Round turn order: ' + ','.join([x.name for x in self._round_turn_order]))


if __name__ == '__main__':
    print('Euchre game functions. run server.py')