#!/usr/bin/env python3

import socket
import threading
import time
import Player
import Euchre
import logging

listen_ip = '192.168.50.128'
listen_port = 9999
all_players_connected = False
card_discard_pile = []
header_length = 10
dealer = ''
player_threads = []
gameover = False

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(threadName)s %(asctime)s: %(message)s')
# logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(threadName)s %(asctime)s: %(message)s')


def player_handle(player_obj, l_condition):
    # First we ask the player for his/her name.
    player_obj.send_data('require_input', 'Welcome. What would you like your player name to be? [1-30 chars] ')
    while True:
        player_name = player_obj.receive_response().lower()
        if any(player for player in euchre.player_order if player.name == player_name):
            player_obj.send_data('require_input',
                           'This name has been chosen, please choose something unique. [1-30 chars] ')
        elif 0 < len(player_name) < 31:  # check length for extra precaution.
            player_obj.name = player_name
            player_obj.send_data('display_message', 'Name accepted. Waiting for all players to join.')
            while player_obj.hand_preference == '':
                player_obj.send_data('require_input', 'Do you prefer to sort your hand by? [suit, value] ')
                hand_pref = player_obj.receive_response()
                if hand_pref in ['suit', 'value']:
                    player_obj.hand_preference = hand_pref
                    player_obj.send_data('display_message', 'Thank you. Waiting for all players to join.')
                    break
            break
        else:
            player_obj.send_data('require_input', 'Name not appropriate, select something else. [1-30 chars] ')
        # send back a packet
    logging.debug('Out of player_name loop')
    with l_condition:
        logging.debug('Waiting for notification from main that all players have connected.')
        l_condition.wait()  # waiting for main to tell us all players have connected and provided names
        logging.debug('all players connected. lock clear.')
    if player_obj is euchre.player_order[0]:
        choose_teams(player_obj)
        with l_condition:
            # tell main thread to continue; teams have been chosen
            l_condition.notify()
    else:
        while len(euchre.team1) < 2 and len(euchre.team2) < 2:
            # loop to notify other players that p1 is choosing teams
            player_obj.send_data('display_message', 'Waiting on %s to pick the teams.' % euchre.player_order[0].name)
            time.sleep(5)

    player_obj.send_data('display_message',
                         'Teams have been chosen and are as follows, team1: %s and %s. team2: %s and %s.' %
                         (euchre.team1[0].name, euchre.team1[1].name, euchre.team2[0].name, euchre.team2[1].name))
    while not player_obj.queue_in.empty() or not gameover:
        task_from_main = player_obj.queue_in.get()
        if task_from_main[0] == 'display_message':
            player_obj.send_data(task_from_main[0], task_from_main[1])
        elif task_from_main[0] == 'require_input':
            player_obj.send_data(task_from_main[0], task_from_main[1])
            player_obj.queue_out.put(player_obj.receive_response())
        elif task_from_main[0] == 'send_line_separator':
            player_obj.send_line_separator()
        else:
            raise Exception('Received a queue_in item i have no idea what to do with!: %s' % task_from_main)

    player_obj.send_data('display_message', 'Thank you for playing. Goodbye.')
    player_obj.socket_object.close()


def choose_teams(player_obj):
    while True:
        team_list = euchre.player_order.copy()
        player_obj.send_data('require_input', 'Hello. You have been chosen to pick the teams. ' +
                             'Please tell me which other player is your teammate. %s, %s, %s [type the name] ' %
                             (euchre.player_order[1].name, euchre.player_order[2].name,
                              euchre.player_order[3].name))
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
                euchre.team1 = team1_temp
                euchre.team2 = team2_temp
                break
    euchre.player_order = [euchre.team1[0], euchre.team2[0], euchre.team1[1], euchre.team2[1]]


def connection_handler(l_condition):
    player_count = 0
    while True:
        # start loop to accept players connections
        client, address = server.accept()
        logging.info('[*] Accepted connection from: %s:%d' % (address[0], address[1]))
        thread_name = 'player%d_thread' % (player_count + 1)
        l_player = Player.Player(client, address[0])
        if player_count < 4:
            # spin up our client thread to handle each of the players
            euchre.player_order.append(l_player)
            client_handler = threading.Thread(target=player_handle, args=(l_player, l_condition), name=thread_name)
            client_handler.start()
            player_count += 1
        else:
            # because of the while loop condition, I don't think this else can occur, but just in case.
            l_player.send_data('display_message', 'Sorry, full on players. Try again next time.')
            client.close()
            del l_player


logging.info('Euchre server starting!')
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((listen_ip, listen_port))
server.listen(5)
logging.info('Listening on %s:%d' % (listen_ip, listen_port))

condition = threading.Condition()
euchre = Euchre.Euchre()
conn_handler = threading.Thread(target=connection_handler, args=(condition,), name='conn_thread')
conn_handler.start()
logging.debug('connection_handler thread started')

# check that all 4 players have names
player_name_count = 0

while player_name_count < 4:
    logging.info('watching player count')
    player_name_count = sum(x.name != '' for x in euchre.player_order)
    logging.info('Players connected: %d\n' % player_name_count)
    time.sleep(3)
with condition:
    condition.notify_all()
    logging.debug('notification sent to player threads that 4 players are connected')

with condition:
    # waiting on teams to be chosen
    condition.wait()

euchre.start_game()

gameover = True
logging.info('gameover')
# todo
# - at some point, some form of sessionizing the players.