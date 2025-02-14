RANKS = '23456789TJQKA'

def card_value(card):
    """Helper function to extract the card value as an integer for comparison."""
    value = card[:-1]  # Remove the suit character
    if value in ['T', 'J', 'Q', 'K', 'A']:
        return {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}[value]
    return int(value)

def closeness(card1, card2):
    """Check if the difference between two cards is less than 5."""
    return abs(card_value(card1) - card_value(card2)) < 5

def suitness(card1, card2):
    """Check if both cards have the same suit."""
    return card1[-1] == card2[-1]

def highness(card1, card2):
    """Check if at least one of the cards is a high card (greater than 9)."""
    return card_value(card1) > 9 or card_value(card2) > 9

def card_rank(card):
    rank = card[:-1]  # Extract rank (handle '10' properly)
    return RANKS.index(rank)