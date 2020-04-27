#!/usr/bin/env python3

import random
import socket
import threading
import time
import Player
import Cards
from queue import Queue

listen_ip = '192.168.50.128'
listen_port = 9999
all_players_connected = False
team1 = []
team2 = []
table_order = []
player_obj_list = []
card_discard_pile = []
process_queue_until_empty: False
header_length = 10


def player_handle(player_obj, queue):
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

    while len(team1) < 2 and len(team2) < 2:
        # loop for picking teams. For simplicity, we let player1 choose the teams
        if all_players_connected:
            if player_obj is player_obj_list[0]:
                choose_teams(player_obj)
            else:
                player_obj.send_data('display_message', 'Waiting on %s to pick the teams.' % player_obj_list[0].name)
                time.sleep(5)
        else:
            time.sleep(3)

    player_obj.send_data('display_message',
                         'Teams have been chosen and are as follows, team1: %s and %s. team2: %s and %s.' %
                         (team1[0].name, team1[1].name, team2[0].name, team2[1].name))

    while player_obj.hand_preference == '':
        player_obj.send_data('require_input', 'Do you prefer to sort your hand by? [suit, value] ')
        hand_pref = player_obj.receive_response().lower()
        if hand_pref in ['suit', 'value']:
            player_obj.hand_preference = hand_pref
            break

    while True:
        if player_obj.hand_preference == 'suit':
            player_obj.hand.sort(key=lambda l_card: l_card.suit)
        elif player_obj.hand_preference == 'value':
            player_obj.hand.sort(key=lambda l_card: l_card.value)
        if not queue.empty():
            task_from_main = queue.get()
            if task_from_main[0] == 'send_data':
                # doesnt yet account for scenarios where we ask for input
                player_obj.send_data(task_from_main[1], task_from_main[2])
            else:
                raise Exception('Received a queue item i have no idea what to do with!: %s' % task_from_main)
        elif player_obj.hand:
            hand_message = 'Your current hand is a follows: \n' + '\n'.join([x.d_value + ' of ' +
                                                                         x.suit for x in player_obj.hand])
            player_obj.send_data('display_message', hand_message)
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


def deal(l_deck, l_card_discard_pile):
    l_deck = l_deck + l_card_discard_pile
    if len(l_deck) != 24:
        raise Exception('Card deck length is not 24!')
    random.shuffle(l_deck)
    print('shuffling cards\n')
    while len(l_deck) > 4:
        for l_player in table_order:
            l_player.hand.append(l_deck.pop(0))
    print('cards have been dealt\n')
    l_card_discard_pile = []
    return l_deck, l_card_discard_pile


def set_turn_order(l_dealer):
    global table_order
    table_order = [team1[0], team2[0], team1[1], team2[1]]
    while table_order.index(l_dealer) != 3:
        # this while statement runs till the dealer is at the end of the list to set the player order.
        shifting = table_order.pop(0)
        table_order.append(shifting)
        print('The player order is: ', table_order)


def connection_handler():
    player_count = 0
    while True:
        # start loop to accept players connections
        client, address = server.accept()
        print('[*] Accepted connection from: %s:%d' % (address[0], address[1]))
        q = Queue()
        thread_name = 'player%d_thread' % (player_count + 1)
        l_player = Player.Player(client, address[0], q, thread_name)
        if player_count < 4:
            # spin up our client thread to handle each of the players
            player_obj_list.append(l_player)
            client_handler = threading.Thread(target=player_handle, args=(l_player, q), name=thread_name )
            client_handler.start()
            player_count += 1
        else:
            # because of the while loop condition, I don't think this else can occur, but just in case.
            player.send_data('display_message', 'Sorry, full on players. Try again next time.')
            client.close()
            del l_player


print('Euchre server starting!\n')
deck = Cards.build_deck()
random.shuffle(deck)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((listen_ip, listen_port))
server.listen(5)
print('Listening on %s:%d\n' % (listen_ip, listen_port))
conn_handler = threading.Thread(target=connection_handler)
conn_handler.start()
print('connection_handler thread started')
cards_dealt = False

# check that all 4 players have names
player_name_count = 0
while player_name_count < 4:
    print('watching player count')
    player_name_count = sum(x.name != '' for x in player_obj_list)
    print('Players connected: %d\n' % player_name_count)
    time.sleep(3)

all_players_connected = True
while len(team1) < 2 and len(team2) < 2: # see if we can change to a thread.lock at some point
    # we wait for teams to be settled
    time.sleep(2)

# determine first dealer
dealer = None
process_queue_until_empty = True
while not dealer:
    queue_first = True
    for player in player_obj_list:
        card = deck.pop(0)
        card_discard_pile.append(card)
        if card.d_value == 'Jack' and (card.suit == 'Spades' or card.suit == 'Clubs'):
            dealer = player
            for b_player in player_obj_list:
                b_player.queue.put(('send_data', 'display_message', '%s got %s and will be the first dealer.' %
                                    (player.name, '%s of %s' % (card.d_value, card.suit))))
            set_turn_order(dealer)
            break
        else:
            for c_player in player_obj_list:
                c_player.queue.put(('send_data', 'display_message', '%s got %s' % (player.name, '%s of %s' %
                                                                                   (card.d_value, card.suit))))

deck, card_discard_pile = deal(deck, card_discard_pile)
for x in player_obj_list:
    print('player %s hand:' % x.name)
    for card in x.hand:
        print('%s of %s' % (card.d_value, card.suit))
while True:
    # print('Team1: ', team1)
    # print('Team2: ', team2)
    time.sleep(5)
# todo
# - let player pick hand display order. Done. needs testing.
# - first black jack deals. done. needs testing.
# - change if/while checks to thread locks if possible.