#!/usr/bin/env python3

import random
import socket
import threading
import time
import Player
import Cards
import Euchre
import logging
from queue import Queue

listen_ip = '192.168.50.128'
listen_port = 9999
all_players_connected = False
team1 = []
team2 = []
player_obj_list = []
card_discard_pile = []
header_length = 10
dealer = ''
player_threads = []

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(threadName)s %(asctime)s: %(message)s')
# logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(threadName)s %(asctime)s: %(message)s')


def player_handle(player_obj, l_condition):
    # First we ask the player for his/her name.
    player_obj.send_data('require_input', 'Welcome. What would you like your player name to be? [1-30 chars] ')
    while True:
        player_name = player_obj.receive_response().lower()
        if any(player for player in player_obj_list if player.name == player_name):
            player_obj.send_data('require_input',
                           'This name has been chosen, please choose something unique. [1-30 chars] ')
        elif 0 < len(player_name) < 31:  # check length for extra precaution.
            player_obj.name = player_name
            player_obj.send_data('display_message', 'Name accepted. Waiting for all players to join.')
            break
        else:
            player_obj.send_data('require_input', 'Name not appropriate, select something else. [1-30 chars] ')
        # send back a packet
    logging.debug('Out of player_name loop')
    with l_condition:
        logging.debug('Waiting for notification from main that all players have connected.')
        l_condition.wait()  # waiting for main to tell us all players have connected and provided names
        logging.debug('all players connected. lock clear.')
    if player_obj is player_obj_list[0]:
        with l_condition:
            choose_teams(player_obj)
            # tell main thread to continue; teams have been chosen
            l_condition.notify()
    else:
        while len(team1) < 2 and len(team2) < 2:
            # loop to notify other players that p1 is choosing teams
            player_obj.send_data('display_message', 'Waiting on %s to pick the teams.' % player_obj_list[0].name)
            time.sleep(5)

    player_obj.send_data('display_message',
                         'Teams have been chosen and are as follows, team1: %s and %s. team2: %s and %s.' %
                         (team1[0].name, team1[1].name, team2[0].name, team2[1].name))
    # with l_condition:
    #     l_condition.wait()
    while not dealer and not player_obj.queue.empty():
        # this loop is for displaying the first black jack deals cards to the players
        task_from_main = player_obj.queue.get()
        if task_from_main[0] == 'send_data':
            # doesnt yet account for scenarios where we ask for input
            player_obj.send_data(task_from_main[1], task_from_main[2])
        else:
            raise Exception('Received a queue item i have no idea what to do with!: %s' % task_from_main)

    while player_obj.hand_preference == '':
        player_obj.send_data('require_input', 'Do you prefer to sort your hand by? [suit, value] ')
        hand_pref = player_obj.receive_response().lower()
        if hand_pref in ['suit', 'value']:
            player_obj.hand_preference = hand_pref
            break

    temp_display_hand = True
    while True:
        if player_obj.hand_preference == 'suit' and len(player_obj.hand) > 1:
            player_obj.hand.sort(key=lambda l_card: l_card.suit)
        elif player_obj.hand_preference == 'value' and len(player_obj.hand) > 1:
            player_obj.hand.sort(key=lambda l_card: l_card.value)
        if not player_obj.queue.empty():
            task_from_main = player_obj.queue.get()
            if task_from_main[0] == 'send_data':
                # doesnt yet account for scenarios where we ask for input
                player_obj.send_data(task_from_main[1], task_from_main[2])
            else:
                raise Exception('Received a queue item i have no idea what to do with!: %s' % task_from_main)
        elif player_obj.hand and temp_display_hand:
            hand_message = 'Your current hand is a follows: \n' + '\n'.join([x.d_value + ' of ' +
                                                                         x.suit for x in player_obj.hand])
            player_obj.send_data('display_message', hand_message)
            temp_display_hand = False
        # time.sleep(0.2)

    player_obj.socket_object.close()


def choose_teams(player_obj):
    global team1
    global team2
    while True:
        team_list = player_obj_list.copy()
        player_obj.send_data('require_input', 'Hello. You have been chosen to pick the teams.' +
                             'Please tell me which other player is your teammate. %s, %s, %s [type the name] ' %
                             (player_obj_list[1].name, player_obj_list[2].name,
                              player_obj_list[3].name))
        p1_teammate_response = player_obj.receive_response()
        # look for the player that p1 responded with. Should only match 1 as names are unique.
        # if no match is found, then p1 mis-typed.
        team_mate = next((l_player for l_player in team_list if l_player.name == p1_teammate_response), None)
        if team_mate:
            player_obj.teammate = team_mate  # set player1's teammate
            team_mate.teammate = player_obj  # set the other player's teammate as player 1
            team1_temp = [player_obj, team_mate]
            team_list.remove(team_mate)
            team_list.remove(player_obj)
            if len(team_list) == 2:
                # should only be 2 players left in the list unless something went wrong
                team_list[0].teammate = team_list[1]
                team_list[1].teammate = team_list[0]  # set the remaining players as each other's team.
                team2_temp = (team_list[0], team_list[1])
            else:
                raise Exception('Player count is wrong!')
            player_obj.send_data('require_input',
                                 '''The teams are as follows, team1: %s and %s. team2: %s and %s. 
                                 Is this correct? [y/n] ''' % (team1_temp[0].name, team1_temp[1].name, team2_temp[0].name,
                                                               team2_temp[1].name))
            team_response_confirm = player_obj.receive_response()
            if team_response_confirm == 'y':
                team1 = team1_temp
                team2 = team2_temp
                break


def connection_handler(l_condition):
    player_count = 0
    while True:
        # start loop to accept players connections
        client, address = server.accept()
        logging.info('[*] Accepted connection from: %s:%d' % (address[0], address[1]))
        q = Queue()
        thread_name = 'player%d_thread' % (player_count + 1)
        l_player = Player.Player(client, address[0], q)
        if player_count < 4:
            # spin up our client thread to handle each of the players
            player_obj_list.append(l_player)
            client_handler = threading.Thread(target=player_handle, args=(l_player, l_condition), name=thread_name)
            client_handler.start()
            player_count += 1
        else:
            # because of the while loop condition, I don't think this else can occur, but just in case.
            l_player.send_data('display_message', 'Sorry, full on players. Try again next time.')
            client.close()
            del l_player


logging.info('Euchre server starting!')
deck = Cards.build_deck()
random.shuffle(deck)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((listen_ip, listen_port))
server.listen(5)
logging.info('Listening on %s:%d' % (listen_ip, listen_port))

condition = threading.Condition()
conn_handler = threading.Thread(target=connection_handler, args=(condition,), name='conn_thread')
conn_handler.start()
logging.debug('connection_handler thread started')

# check that all 4 players have names
player_name_count = 0

while player_name_count < 4:
    logging.info('watching player count')
    player_name_count = sum(x.name != '' for x in player_obj_list)
    logging.info('Players connected: %d\n' % player_name_count)
    time.sleep(3)
with condition:
    condition.notify_all()
    logging.debug('notification sent to player threads that 4 players are connected')

with condition:
    # waiting on teams to be chosen
    condition.wait()

dealer, deck, card_discard_pile = Euchre.get_first_dealer(player_obj_list, deck, card_discard_pile)

table_order = Euchre.set_turn_order(dealer, team1, team2)
deck, card_discard_pile = Euchre.deal(deck, card_discard_pile, table_order)

while True:
    # print('Team1: ', team1)
    # print('Team2: ', team2)
    time.sleep(5)
# todo
# - first black jack deals. done. needs testing.
# - change if/while checks to thread locks if possible.