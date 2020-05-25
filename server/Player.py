import json
import logging
from queue import Queue


class Player:
    def __init__(self, socket_object, address, sock_header_length=10):
        """
        :param socket_object: pass a socket object opened with a client after running socket.accept()
        :param address: The IP address of the client for logging purposes
        :param q: queue object for passing data to Player
        :param sock_header_length: used to specify a header length for data sent to the players. Default is 10.
        """
        self.name = ''
        self.hand = []
        self.socket_object = socket_object
        self.teammate = ''
        self.address = address
        self.hand_preference = ''
        self.queue_in = Queue()
        self.queue_out = Queue()
        self.sock_header_length = sock_header_length
        self.logger = logging.getLogger()

    def receive_response(self):
        response_header = self.socket_object.recv(self.sock_header_length)
        if not len(response_header):
            self.logger.info('Player %s closed connection' % self.name)
        response_length = int(response_header.decode().strip())
        data = b''
        while len(data) < response_length:
            packet = self.socket_object.recv(response_length - len(data))
            if not packet:
                return None
            data += packet
        data = data.decode()
        self.logger.debug('Received request: %s from: %s' % (data, self.address))
        return data

    def send_data(self, instruction, message):
        """
        :param instruction: display_message or require_input
        :param message: what you want to send to the player
        :return: none
        """
        instructions = ['display_message', 'require_input']
        if instruction not in instructions:
            raise ValueError("Invalid instruction. Expected one of: %s" % instructions)
        player_request = {'instruction': instruction, 'message': message}
        data = json.dumps(player_request)
        data_header = f'{len(data):<{self.sock_header_length}}'
        msg = data_header + data
        self.socket_object.send(msg.encode())
        self.logger.debug('Sent data: %s to: %s. length: %d encode_len: %d' % (msg, self.address,
                                                                        len(msg), len(msg.encode())))

    def send_line_separator(self, newlines=True):
        """
        send a line separator created with = to the player.
        :param newlines: default: True. Include a blank line before and after the separator
        :return: None.
        """
        if newlines:
            self.send_data('display_message', '\n' + '=' * 80 + '\n')
        else:
            self.send_data('display_message', '=' * 80)

    def display_hand(self):
        """
        sorts the hand as the player has specified, and constructs a message to be sent to the player, adds to their queue
        :return None: 
        """
        if self.hand_preference == 'suit' and len(self.hand) > 1:
            self.hand.sort(key=lambda l_card: l_card.suit)
        elif self.hand_preference == 'value' and len(self.hand) > 1:
            self.hand.sort(key=lambda l_card: l_card.value)
        else:
            raise Exception('Player has no hand to display')
        hand_message = 'Your current hand is a follows: \n' + '\n'.join([x.d_value + ' of ' +
                                                                         x.suit for x in self.hand])
        self.queue_in.put(['display_message', hand_message])


if __name__ == '__main__':
    print('Player class. import into another script to use. or run server.py')