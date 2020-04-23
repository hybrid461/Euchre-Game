#!/usr/bin/env python3

import socket
import sys
import json

server_ip = '192.168.50.128'
server_port = 9999

# create the socket object
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect the client to the game server
try:
    client.connect((server_ip, server_port))
    print('Connected to server %s on port %s' % (server_ip, server_port))
except Exception as e:
    print('Failed to connect to game server. Error: %s' % e)
    sys.exit()

# main loop
while True:
    response = client.recv(4096).decode()
    # print('DEBUG: ', type(response), response)
    if response == '':
        print('Server closed connection.')
        break
    json_list = response.split('}{')
    for item in json_list:
        # this next bit of code handles where two or more json requests are received
        if not item.startswith('{'):
            item = '{' + item
        if not item.endswith('}'):
            item = item + '}'
        try:
            message_dict = json.loads(item)
        except json.decoder.JSONDecodeError:
            print('json decode error with item: %s. full data off socket: %s' % (item, response))
        # print(type(message_dict), message_dict)
        try:
            if message_dict['instruction'] == 'display_message':
                print(message_dict['message'])
            elif message_dict['instruction'] == 'require_input':
                player_input = input(message_dict['message'])
                while len(player_input) > 255:
                    print('Not accepting data longer than 255 characters, enter again.\n')
                    player_input = input(message_dict['message'])
                client.send(player_input.encode())
            else:
                print('instruction invalid.')
        except Exception as e:
            print('Looks like we got a response we were not expecting. Error: %s' % e)

client.close()