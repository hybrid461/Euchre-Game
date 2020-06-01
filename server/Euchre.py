import random
import logging
import time
import Cards
import re

module_logger = logging.getLogger()

class Euchre:
    def __init__(self):
        self.dealer = None
        self.player_order = []
        self.team1 = []
        self.team2 = []
        self.team1_points = 0
        self.team2_points = 0
        self.deck = Cards.build_deck()
        self.card_discard_pile = []
        self.gameplay_obj = None

    def start_game(self):
        random.shuffle(self.deck)
        self.get_first_dealer()
        self.start_round()

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
        while self.team1_points < 10 and self.team2_points < 10:
            self.gameplay_obj = Gameplay(self.player_order)
            self.set_player_order()
            self.deal()
            self.show_all_players_their_hands()
            trump_chooser = self.pick_trump()
            if not trump_chooser:
                self.card_discard_pile += self.gameplay_obj.discard_pile
                for l_player in self.player_order:
                    self.card_discard_pile += l_player.hand
                    l_player.hand = []
                self.gameplay_obj.discard_pile = []
                self.pick_next_dealer()
                continue
            else:
                self._setup_round_teams(trump_chooser)  # must run before build_round_order
                self.go_alone(trump_chooser)
                self.build_round_order()
                self.gameplay_obj.start()
                self.calc_points()
                self.card_discard_pile += self.gameplay_obj.discard_pile
                self.gameplay_obj.discard_pile = []
                self.pick_next_dealer()

        if self.team1_points >= 10:
            message = 'GAMEOVER. Congratulations to %s and %s for winning with %d points.' % (self.team1[0].name,
                                                                                             self.team1[1].name,
                                                                                             self.team1_points)
        else:
            message = 'GAMEOVER. Congratulations to %s and %s for winning with %d points.' % (self.team2[0].name,
                                                                                             self.team2[1].name,
                                                                                             self.team2_points)
        for x_player in self.player_order:
            x_player.queue_in.put(['display_message', message])

    def deal(self):
        l_deck = self.deck + self.card_discard_pile
        logging.debug('In Euchre.deal, len(Euchre.deck)=%d, len(Euchre.card_discard_pile)=%d' %
                      (len(self.deck), len(self.card_discard_pile)))
        for l_player in self.player_order:
            if len(l_player.hand) > 0:
                l_deck += l_player.hand
                logging.debug('In Euchre.deal, adding player: %s hand_size: %d to l_deck(size): %d' %
                              (l_player.name, len(l_player.hand), len(l_deck)))
                l_player.hand = []
        if len(l_deck) != 24:
            raise Exception('Card deck length is not 24! Length: %d' % len(l_deck))
        random.shuffle(l_deck)
        module_logger.info('shuffling cards')
        while len(l_deck) > 4:
            for l_player in self.player_order:
                l_player.hand.append(l_deck.pop(0))
        module_logger.info('cards have been dealt')
        self.card_discard_pile = []
        self.deck = []
        self.gameplay_obj.round_kitty = l_deck

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
        trump_card = self.gameplay_obj.round_kitty.pop(0)
        self.card_discard_pile += self.gameplay_obj.round_kitty
        self.gameplay_obj.round_kitty = []
        trump_chooser = self._trump_opt_1(trump_card)
        if not trump_chooser:
            trump_chooser = self._trump_opt_2(trump_card)
            self.card_discard_pile.append(trump_card)
        return trump_chooser
    
    def _trump_opt_1(self, trump_card):
        """
        players choose trump based on top card from kitty pile
        :param trump_card: top card of kitty pile
        :return: 
        """
        first_trump_str = '%s of %s' % (trump_card.d_value, trump_card.suit)
        trump_chooser = None
        for l_player in self.player_order:
            l_player.queue_in.put(['display_message', '%s is up for trump. %s chooses first.' %
                                   (first_trump_str, self.player_order[0].name)])
        for l_player in self.player_order:
            trump_selected = False
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
                    self.gameplay_obj.trump = trump_card.suit
                    self.dealer_pick_up_card(trump_card, first_trump_str)
                    trump_selected = True
                    trump_chooser = l_player
                    self._player_has_chosen_trump(l_player)
                    break
                elif trump_response == '2':
                    self._player_has_passed(l_player)
                    break
                else:
                    continue
            if trump_selected:
                break
        return trump_chooser
    
    def _trump_opt_2(self, trump_card):
        """
        players choose trump based on the suits in their hand. They cannot choose what was passed on from the kitty pile
        :param trump_card: the card that was on top of the kitty pile.
        :return: 
        """
        trump_chooser = None
        trump_selected = False
        for l_player in self.player_order:
            l_player.queue_in.put(['send_line_separator'])
            l_player.queue_in.put(['display_message', 'Another suit for trump may now be chosen'])
            l_player.queue_in.put(['send_line_separator'])
        for l_player in self.player_order:
            l_player.queue_in.put(['send_line_separator'])
            l_player.display_hand()
            options_set = set([x.suit for x in l_player.hand if x.suit != trump_card.suit])
            options_set.add('pass')
            trump_option_str = 'Your options for trump are as follows: ['
            trump_option_str += ', '.join(options_set) + '] '
            while True:
                l_player.queue_in.put(['require_input', trump_option_str])
                l_player_resp = l_player.queue_out.get()
                if l_player_resp not in options_set:
                    continue
                else:
                    if l_player_resp == 'pass':
                        self._player_has_passed(l_player)
                        break
                    else:
                        trump_selected = True
                        trump_chooser = l_player
                        self.gameplay_obj.trump = l_player_resp
                        self._player_has_chosen_trump(l_player)
                        break
            if trump_selected:
                break
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
        trump_chooser_index = self.gameplay_obj.round_off_team.index(trump_chooser)
        if trump_chooser_index == 0:
            off_teammate_index = 1
        else:
            off_teammate_index = 0
        off_teammate = self.gameplay_obj.round_off_team[off_teammate_index]
        o_alone_player = self.go_alone_question([trump_chooser, off_teammate])
        if o_alone_player:
            self.gameplay_obj.round_off_team = [o_alone_player]
            for x_player in self.player_order:
                x_player.queue_in.put(['display_message', '%s has chosen to go alone' % o_alone_player.name])
        d_alone_player = self.go_alone_question(self.gameplay_obj.round_def_team)
        if d_alone_player:
            self.gameplay_obj.round_def_team = [d_alone_player]
            for x_player in self.player_order:
                x_player.queue_in.put(['display_message', '%s has chosen to go alone' % d_alone_player.name])

    def go_alone_question(self, team_list):
        for l_player in team_list:
            l_player.display_hand()
            l_player.queue_in.put(['require_input', 'Do you wish to play alone this round? [1 = no, 2 = yes] '])
            go_alone_response = l_player.queue_out.get()
            if go_alone_response == '1':
                module_logger.info('%s chose to not go alone' % l_player.name)
                continue
            elif go_alone_response == '2':
                return l_player

    def _player_has_passed(self, l_player):
        for x_player in self.player_order:
            x_player.queue_in.put(['display_message', '%s has passed.' % l_player.name])

    def _player_has_chosen_trump(self, l_player):
        for x_player in self.player_order:
            x_player.queue_in.put(['display_message', '%s has chosen %s as trump for this round' %
                                   (l_player.name, self.gameplay_obj.trump)])
            x_player.queue_in.put(['send_line_separator'])

    def _setup_round_teams(self, trump_chooser):
        if trump_chooser in self.team1:
            self.gameplay_obj.round_off_team = self.team1
            self.gameplay_obj.round_def_team = self.team2
        else:
            self.gameplay_obj.round_off_team = self.team2
            self.gameplay_obj.round_def_team = self.team1

    def build_round_order(self):
        for l_player in self.player_order:
            if l_player in self.gameplay_obj.round_off_team:
                self.gameplay_obj.round_turn_order.append(l_player)
            elif l_player in self.gameplay_obj.round_def_team:
                self.gameplay_obj.round_turn_order.append(l_player)
        module_logger.info('Round turn order: ' + ','.join([x.name for x in self.gameplay_obj.round_turn_order]))

    def calc_points(self):
        defend_alone = False
        offend_alone = False
        if len(self.gameplay_obj.round_def_team) == 1:
            defend_alone = True
        if len(self.gameplay_obj.round_off_team) == 1:
            offend_alone = True
        if self.gameplay_obj.round_off_tricks > self.gameplay_obj.round_def_tricks:
            tricks = self.gameplay_obj.round_off_tricks
            if tricks == 5:
                if offend_alone:
                    points = 4
                else:
                    points = 2
            elif tricks >= 3:
                points = 1
            else:
                raise Exception('gameplay object round tricks are incorrect')
            if self.gameplay_obj.round_off_team[0] in self.team1:
                self.team1_points += points
                tally_string = '%s and %s gained %d points' % (self.team1[0].name, self.team1[1].name, points)
            else:
                self.team2_points += points
                tally_string = '%s and %s gained %d points' % (self.team2[0].name, self.team2[1].name, points)
        else:
            tricks = self.gameplay_obj.round_def_tricks
            if tricks == 5 and defend_alone:
                points = 4
            elif tricks >= 3:
                points = 2
            if self.gameplay_obj.round_def_team[1] in self.team1:
                self.team1_points += points
                tally_string = '%s and %s gained %d points' % (self.team1[0].name, self.team1[1].name, points)
            else:
                self.team2_points += points
                tally_string = '%s and %s gained %d points' % (self.team2[0].name, self.team2[1].name, points)

        tally_string += '\nCurrent total:\n%s and %s: %d\n%s and %s: %d' % (self.team1[0].name, self.team1[1].name,
                                                                           self.team1_points, self.team2[0].name,
                                                                            self.team2[1].name, self.team2_points)
        for l_player in self.player_order:
            l_player.queue_in.put(['display_message', tally_string])

    def pick_next_dealer(self):
        self.dealer = self.player_order[0]
        message = 'Onto the next round, the dealer will be: %s ' % self.dealer.name
        for l_player in self.player_order:
            l_player.queue_in.put(['display_message', message])
            l_player.queue_in.put(['send_line_separator'])


class Gameplay:
    def __init__(self, full_player_order):
        self.full_player_order = full_player_order
        self.round_off_team = None
        self.round_def_team = None
        self.round_off_tricks = 0
        self.round_def_tricks = 0
        self.round_turn_order = []
        self.round_kitty = []
        self.discard_pile = []
        self.trump = ''
        self.left_bower = None
        self.right_bower = None
        
    def start(self):
        self.set_bowers()
        trick_count = 0
        while trick_count < 5:
            trick, lead_suit = self.play_cards()
            winner = self.who_won(trick)
            self.add_tricks(winner)
            self.shift_round_order(winner)
            trick_count += 1
        # round play complete

    def set_bowers(self):
        self.right_bower = Cards.Card(self.trump, 'Jack', 11)
        if self.trump == 'Hearts':
            self.left_bower = Cards.Card('Diamonds', 'Jack', 11)
        elif self.trump == 'Diamonds':
            self.left_bower = Cards.Card('Hearts', 'Jack', 11)
        elif self.trump == 'Spades':
            self.left_bower = Cards.Card('Clubs', 'Jack', 11)
        else:
            self.left_bower = Cards.Card('Spades', 'Jack', 11)

    def play_cards(self):
        trick = {}
        lead_suit = None
        for l_player in self.round_turn_order:
            card_played = self.choose_card(l_player, lead_suit)
            for x_player in self.full_player_order:
                x_player.queue_in.put(['display_message', '%s has played %s of %s' %
                                       (l_player.name, card_played.d_value, card_played.suit)])
            if not lead_suit:
                if card_played.d_value == self.left_bower.d_value and card_played.suit == self.left_bower.suit:
                    lead_suit = self.trump
                else:
                    lead_suit = card_played.suit
                for x_player in self.full_player_order:
                    x_player.queue_in.put(['display_message', 'Players must follow suit. Lead suit: ' + lead_suit])
            trick[l_player] = card_played
        return trick, lead_suit

    def who_won(self, trick_dict):
        """
        :param trick_dict: dictionary of the players and the cards they played during the trick
        :return: winner. Player who won the trick
        """
        winner = None
        for player, card in trick_dict.items():
            module_logger.debug('Euchre.who_won, player: %s card.d_value: %s, card.suit: %s' %
                                (player.name, card.d_value,card.suit))
            if card.suit == self.right_bower.suit and card.value == self.right_bower.value:
                winner = [player, card]
                module_logger.debug('''Euchre.who_won, winner[player.name]: %s, winner[card.d_value]: %s, 
winner[card.suit]: %s ''' % (winner[0].name, winner[1].d_value, winner[1].suit))
                break
            if not winner:  # put first player in as something to compare to.
                winner = [player, card]
                module_logger.debug('''Euchre.who_won, winner[player.name]: %s, winner[card.d_value]: %s, 
winner[card.suit]: %s ''' % (winner[0].name, winner[1].d_value, winner[1].suit))
            else:
                if winner[1].suit == self.left_bower.suit and winner[1].value == self.left_bower.value:
                    module_logger.debug('''Euchre.who_won, winner[player.name]: %s, winner[card.d_value]: %s, 
winner[card.suit]: %s ''' % (winner[0].name, winner[1].d_value, winner[1].suit))
                    continue
                if winner[1].suit == self.trump:
                    if card.suit == self.trump:
                        if card.value > winner[1].value:
                            winner = [player, card]
                    elif card.suit == self.left_bower.suit and card.value == self.left_bower.value and \
                            winner[1].value != self.right_bower.value:
                        # ensure left bower beats out other trump leaders.
                        winner = [player, card]
                else: # current trick winner is not trump
                    if card.suit == self.trump or card.value == self.left_bower.value \
                            and card.suit == self.left_bower.suit: # any trump beats not trump
                        winner = [player, card]
                    elif card.value > winner[1].value and winner[1].suit == card.suit:
                        # if offsuit matches and is higher value
                        winner = [player, card]
                module_logger.debug('''Euchre.who_won, winner[player.name]: %s, winner[card.d_value]: %s, 
winner[card.suit]: %s ''' % (winner[0].name, winner[1].d_value, winner[1].suit))
        for x_player in self.full_player_order:
            x_player.queue_in.put(['display_message', '%s won with %s of %s' %
                                   (winner[0].name, winner[1].d_value, winner[1].suit)])
        return winner[0]

    def choose_card(self, l_player, lead_suit):
        while True:
            if not lead_suit:
                play_string = 'You\'re first, which card do you want to play [enter the number]: \n' + \
                              '\n'.join(['[%d] ' % (l_player.hand.index(x)) + x.d_value + ' of ' +
                                        x.suit for x in l_player.hand]) + '\n'
            else:
                if lead_suit == self.trump:
                    # we want to ensure the left bower is accounted for.
                    options_list = ['[%d] ' % (l_player.hand.index(x)) + x.d_value + ' of ' +
                                    x.suit for x in l_player.hand if x.suit == lead_suit or
                                   (x.suit == self.left_bower.suit and x.d_value == self.left_bower.d_value)]
                    if not options_list:
                        # should account for a player who doesnt have to follow suit
                        play_string = 'Which card do you want to play [enter the number]: \n' + \
                                      '\n'.join(['[%d] ' % (l_player.hand.index(x)) + x.d_value + ' of ' +
                                                 x.suit for x in l_player.hand]) + '\n'
                    else:
                        play_string = 'Which card do you want to play (must follow suit) [enter the number]: \n' + \
                                  '\n'.join(options_list) + '\n'
                else:
                    options_list = ['[%d] ' % (l_player.hand.index(x)) + x.d_value + ' of ' +
                                             x.suit for x in l_player.hand if x.suit == lead_suit and
                                    (x.d_value != self.left_bower.d_value or x.suit != self.left_bower.suit)]
                    if not options_list:
                        # should account for a player who doesnt have to follow suit
                        play_string = 'Which card do you want to play [enter the number]: \n' + \
                                      '\n'.join(['[%d] ' % (l_player.hand.index(x)) + x.d_value + ' of ' +
                                                 x.suit for x in l_player.hand]) + '\n'
                    else:
                        play_string = 'Which card do you want to play (must follow suit) [enter the number]: \n' + \
                            '\n'.join(options_list) + '\n'
            options = re.findall('\d+', play_string)
            l_player.queue_in.put(['display_message', 'Reminder that trump is currently: ' + self.trump])
            l_player.queue_in.put(['require_input', play_string])
            l_player_resp = l_player.queue_out.get()
            if l_player_resp in options:
                card_played = l_player.hand.pop(int(l_player_resp))
                self.discard_pile.append(card_played)
                break

        return card_played

    def add_tricks(self, winner):
        if winner in self.round_def_team:
            self.round_def_tricks += 1
        else:
            self.round_off_tricks += 1
        for x_player in self.full_player_order:
            message = 'Current trick count: \n%s and %s: %d' % \
                      (self.round_def_team[0].name, self.round_def_team[0].teammate.name, self.round_def_tricks)
            message += '\n%s and %s: %d' % \
                      (self.round_off_team[0].name, self.round_off_team[0].teammate.name, self.round_off_tricks)
            x_player.queue_in.put(['display_message', message])
            x_player.queue_in.put(['send_line_separator'])

    def shift_round_order(self, winner):
        module_logger.info('Current round player order: ' + ','.join([x.name for x in self.round_turn_order]))
        while self.round_turn_order.index(winner) != 0:
            # this while statement runs till the winner of the last round is first to go on the next one.
            shifting = self.round_turn_order.pop(0)
            self.round_turn_order.append(shifting)
        module_logger.info('Updated round player order: ' + ','.join([x.name for x in self.round_turn_order]))


if __name__ == '__main__':
    print('Euchre game functions. run server.py')

# todo
