#!/usr/bin/env python3

import socket
import sys
import json

server_ip = '192.168.20.178'
server_port = 9999

def receive_data(client, header_length):
    response_header = client.recv(header_length)
    if not len(response_header):
        return None
    response_length = int(response_header.decode().strip())
    # print('DEBUG: ', type(response_length), response_length)
    data = b''
    while len(data) < response_length:
        packet = client.recv(response_length - len(data))
        if not packet:
            return None
        data += packet
    data = data.decode()
    # print('DEBUG: ', type(data), data, 'length: %d' % len(data))
    return data


def connect_to_server():
    # create the socket object
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # connect the client to the game server
    try:
        client.connect((server_ip, server_port))
        print('Connected to server %s on port %s' % (server_ip, server_port))
        return client
    except Exception as e:
        print('Failed to connect to game server. Error: %s' % e)
        sys.exit()


def main():
    client = connect_to_server()
    header_length = 10
    # main loop
    while True:
        response = receive_data(client, header_length)
        if not response:
            print('Server closed connection')
            sys.exit()
        else:
            message_dict = json.loads(response)
            try:
                if message_dict['instruction'] == 'display_message':
                    print(message_dict['message'])
                elif message_dict['instruction'] == 'require_input':
                    player_input = input(message_dict['message'])
                    while len(player_input) > 255:
                        print('Not accepting data longer than 255 characters, enter again.\n')
                        player_input = input(message_dict['message'])
                    data_header = f'{len(player_input):<{header_length}}'
                    msg = data_header + player_input
                    client.send(msg.encode())
                else:
                    print('instruction invalid.')
            except Exception as e:
                print('Looks like we got a response we were not expecting. Error: %s' % e)

    client.close()


if __name__ == '__main__':
    main()