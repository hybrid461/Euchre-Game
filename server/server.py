#!/usr/bin/env python3

import random
import socket
import threading
import time
import Player
import Cards


listen_ip = '0.0.0.0'
listen_port = 9999
all_players_connected = False
team1 = []
team2 = []
player_obj_list = []


def player_handle(player_obj):
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
        # print('at team choosing loop. all_players_connected: %s. player_obj: %s player_obj_list: %s' %
        #       (all_players_connected, player_obj, player_obj_list))
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
                         '''Teams have been chosen and are as follows, team1: %s and %s. team2: %s and %s.''' %
                   (team1[0].name, team1[1].name, team2[0].name, team1[0].name))

    player_obj.socket_object.close()


def choose_teams(player_obj):
    global team1
    global team2
    team_list = player_obj_list.copy()
    while True:
        player_obj.send_data('require_input', '''Hello. You have been chosen to pick the teams. 
                        Please tell me which other player is your teammate. %s, %s, %s [type the name] ''' %
                             (player_obj_list[1].name, player_obj_list[2].name,
                              player_obj_list[3].name))
        p1_teammate_response = player_obj.receive_response()
        # look for the player that p1 responded with. Should only match 1 as names are unique.
        # if no match is found, then p1 mis-typed.
        team_mate = next((player for player in team_list if player.name == p1_teammate_response), None)
        if team_mate:
            player_obj.teammate = team_mate  # set player1's teammate
            team_mate.teammate = player_obj  # set the other player's teammate as player 1
            team1 = [player_obj, team_mate]
            team_list.remove(team_mate)
            team_list.remove(player_obj)
            if len(team_list) == 2:
                # should only be 2 players left in the list unless something went wrong
                team_list[0].teammate = team_list[1]
                team_list[1].teammate = team_list[0]  # set the remaining players as each other's team.
                team2 = (team_list[0], team_list[1])
            else:
                raise Exception('Player count is wrong!')
            player_obj.send_data('require_input',
                                 '''The teams are as follows, team1: %s and %s. team2: %s and %s. 
                                 Is this correct? [y/n] ''' % (team1[0].name, team1[1].name, team2[0].name,
                                                               team1[0].name))
            team_response_confirm = player_obj.receive_response()
            if team_response_confirm == 'y':
                break


def deal(l_deck, players):
    random.shuffle(l_deck)
    print('shuffling cards\n')
    while len(deck) > 4:
        for player in players:
            player.hand.append(deck.pop(0))
    print('cards have been dealt\n')
    return l_deck


def connection_handler():
    player_count = 0
    while True:
        # start loop to accept players connections
        client, address = server.accept()
        print('[*] Accepted connection from: %s:%d' % (address[0], address[1]))
        player = Player.Player(client, address[0])
        if player_count < 4:
            # spin up our client thread to handle each of the players
            player_obj_list.append(player)
            client_handler = threading.Thread(target=player_handle(player))
            client_handler.start()
            player_count += 1
        else:
            # because of the while loop condition, I don't think this else can occur, but just in case.
            player.send_data('display_message', 'Sorry, full on players. Try again next time.')
            client.close()
            del player


print('Euchre server starting!\n')
deck = Cards.build_deck()

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
deal(deck, player_obj_list)
for x in player_obj_list: print(x.hand)

# todo
# - let player pick hand display order.