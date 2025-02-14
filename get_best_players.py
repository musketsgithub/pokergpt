from parse_files import get_total_hands, parse_hand_history
import re
from utils.poker_parser import get_player_contribution
import matplotlib.pyplot as plt
import json

total_hands = get_total_hands()

player_dict = {}

for i, hand in enumerate(total_hands[:1]):
    print(f"Hand {i+1}/{len(total_hands)}")

    if "cashed out the hand for" in hand or "Main pot" in hand:
        continue

    # print(hand)

    # Replace stage names (HOLE CARDS, FLOP, TURN, RIVER) with the corresponding action stage names
    action_history = hand.replace('*** HOLE CARDS ***', 'PREFLOP')\
                     .replace('*** FLOP ***', 'FLOP')\
                     .replace('*** TURN ***', 'TURN')\
                     .replace('*** RIVER ***', 'RIVER')

    # Filter relevant lines (action-related lines only)
    keywords = ["PREFLOP", "FLOP", "TURN", "RIVER", "posts", "checks", "bets", "folds", "raises", "calls"]
    relevant_lines = [line for line in action_history.split('\n') if any(keyword in line for keyword in keywords)]
    action_history = '\n'.join(relevant_lines).strip()

    players = re.findall(r"Seat (\d+): ([\s\S]+?) \(\$([0-9.]+) in chips\)(?:.*?(is sitting out))?", hand, re.MULTILINE)

    # Prepare a list of players who are still in the game (not sitting out)
    playing_players = [
        name for seat, name, chips, status in players if not status
    ]
    num_playing_players = len(playing_players)

    contributions_from_players = {}

    winning_player = None
    for player in playing_players:
        if player not in player_dict:
            player_dict[player]={'hands_played':0, 'winnings':[]}

        contribution = sum([get_player_contribution(_round, player) for _round in parse_hand_history(action_history)])

        contributions_from_players[player] = contribution

        pattern = r"^([^\n]+) collected \$([\d.]+)(?: from (?:the )?pot)?$"
        for line in hand.splitlines():  # Process each line separately
            match = re.match(pattern, line)
            if match:
                winning_player = match.group(1)  # Get the captured name

    # print(winning_player)

    for player in playing_players:
        player_dict[player]['hands_played']+=1
        if player==winning_player:
            player_dict[player]['winnings'].append(sum([contributions_from_players[other_player] for other_player in contributions_from_players if other_player != winning_player]))
        else:
            player_dict[player]['winnings'].append(-contributions_from_players[player])

for player in player_dict:
    player_dict[player]['mbb_hand'] = sum(player_dict[player]['winnings'])/player_dict[player]['hands_played']

print(player_dict)

# with open('play_dict.json', 'w') as json_file:
#     json.dump(player_dict, json_file)
#
# # Load data from JSON file (assuming you have 'play_dict.json' with the correct structure)
# import matplotlib.pyplot as plt
# import json
#
# # Load data from JSON file
# with open('play_dict.json', 'r') as json_file:
#     player_dict = json.load(json_file)
#
# # # Extract player names and hands played
# players = list(player_dict.keys())
# # hands_played = [player_dict[player]['hands_played'] for player in players]
#
# for player in player_dict:
#     player_dict[player]['mbb_hand'] = sum(player_dict[player]['winnings'])/player_dict[player]['hands_played']
#
# mbbs_hand = [player_dict[player]['mbb_hand'] for player in players if player_dict[player]['hands_played']>300]
#
# # Create the histogram with more bins
# plt.hist(mbbs_hand, bins=20, edgecolor='black')  # Increased bins to 20
#
# # Add labels and title
# plt.xlabel('MBB/hand')
# plt.ylabel('Number of Players')
# plt.title('Distribution of Hands Played')
#
# # Show the plot
# plt.show()