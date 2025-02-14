from collections import Counter
from utils.get_card_data import card_rank
from itertools import combinations

RANKS = '23456789TJQKA'

def is_straight(ranks):
    sorted_ranks = sorted(set(ranks))
    if len(sorted_ranks) < 5:
        return False
    for i in range(len(sorted_ranks) - 4):
        if sorted_ranks[i:i+5] == list(range(sorted_ranks[i], sorted_ranks[i] + 5)):
            return True
    return set(ranks) == {0, 1, 2, 3, 12}  # Special case: A-2-3-4-5

def is_flush(cards):
    suit_counts = Counter(card[-1] for card in cards)
    for suit, count in suit_counts.items():
        if count >= 5:
            return True
    return False

def rank_to_str(rank):
    return '10' if rank == 8 else RANKS[rank]

def hand_rank(hand):
    ranks = sorted((card_rank(card) for card in hand), reverse=True)
    rank_counts = Counter(ranks)
    counts = sorted(rank_counts.values(), reverse=True)
    flush = is_flush(hand)
    straight = is_straight(ranks)

    if straight and flush:
        return (8, max(ranks), f"Straight flush: {', '.join(rank_to_str(r) for r in sorted(ranks, reverse=True))}")
    if 4 in counts:
        four_rank = [k for k, v in rank_counts.items() if v == 4][0]
        return (7, four_rank, f'Four of a kind: {rank_to_str(four_rank)}s')
    if counts == [3, 2]:
        three_rank = [k for k, v in rank_counts.items() if v == 3][0]
        return (6, three_rank, f'Full house: {rank_to_str(three_rank)}s full of {rank_to_str(min(rank_counts, key=rank_counts.get))}s')
    if flush:
        return (5, ranks, f"Flush: {', '.join(rank_to_str(r) for r in sorted(ranks, reverse=True))}")
    if straight:
        return (4, max(ranks), f"Straight: {', '.join(rank_to_str(r) for r in sorted(ranks, reverse=True))}")
    if 3 in counts:
        three_rank = [k for k, v in rank_counts.items() if v == 3][0]
        return (3, three_rank, f'Three of a kind: {rank_to_str(three_rank)}s')
    if counts == [2, 2, 1]:
        pairs = sorted([k for k, v in rank_counts.items() if v == 2], reverse=True)
        return (2, pairs, f'Two pair: {rank_to_str(pairs[0])}s and {rank_to_str(pairs[1])}s')
    if 2 in counts:
        pair_rank = [k for k, v in rank_counts.items() if v == 2][0]
        return (1, pair_rank, f'One pair: {rank_to_str(pair_rank)}s')
    return (0, ranks, f"High card: {', '.join(rank_to_str(r) for r in sorted(ranks, reverse=True))}")

def best_hand(hole_cards, community_cards):
    all_cards = hole_cards + community_cards
    best = max((hand for i in range(2, min(8, len(all_cards) + 1)) for hand in combinations(all_cards, i)), key=hand_rank)
    return hand_rank(best)[2]