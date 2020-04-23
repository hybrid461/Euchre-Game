import json


class Player:
    def __init__(self, socket_object, address, q, thread_name=''):
        """
        :param socket_object: pass a socket object opened with a client after running socket.accept()
        :param address: The IP address of the client for logging purposes
        """
        self.name = ''
        self.hand = []
        self.socket_object = socket_object
        self.teammate = ''
        self.address = address
        self.hand_preference = ''
        self.queue = q
        self.thread_name = thread_name

    def receive_response(self):
        response = self.socket_object.recv(1024).decode()
        print('%s - Received request: %s from: %s' % (self.thread_name, response, self.address))
        return response

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
        self.socket_object.send(data.encode())
        print('%s - Sent data: %s to: %s' % (self.thread_name, data, self.address))


if __name__ == '__main__':
    print('Player class. import into another script to use.')