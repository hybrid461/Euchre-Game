class Card:
    def __init__(self, suit, d_value, value):
        self.suit = suit
        self.value = value
        self.d_value = d_value


def build_deck(style='euchre'):
    """
    build_deck should only be run once.
    :param: style = Default: euchre. Option: all. Choose if you want a Euchre deck or deck with all cards.
    :return list of Card() based on style of deck requested:
    """
    deck = []
    if style == 'euchre':
        values = euchre_cards
    elif style == 'all':
        values = all_cards
    else:
        raise ValueError
    for display, value in values.items():
        for suit in suits:
            card = Card(suit, display, value)
            deck.append(card)
    return deck


suits = ['Clubs', 'Spades', 'Hearts', 'Diamonds']
all_cards = {'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5, 'Six': 6, 'Seven': 7, 'Eight': 8,
             'Nine': 9, 'Ten': 10, 'Jack': 11, 'Queen': 12, 'King': 13, 'Ace': 14}
euchre_cards = {'Nine': 9, 'Ten': 10, 'Jack': 11, 'Queen': 12, 'King': 13, 'Ace': 14}
if __name__ == '__main__':
    print('Cards class and build_deck function. import into another script to use. or run server.py')