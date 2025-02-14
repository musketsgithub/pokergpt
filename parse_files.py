import os
import re
from utils.poker_parser import get_player_order, get_last_round_and_board, best_hand, get_pot_contributions, get_legal_moves, get_current_bet, get_player_contribution, parse_hand_history, construct_prompt
from utils.get_card_data import closeness, highness, suitness
import random
import json


import os

def get_total_hands():
    total_hands = []
    folder_path = 'data/pokerstars'

    folders = [f for f in sorted(os.listdir(folder_path)) if os.path.isdir(os.path.join(folder_path, f))]

    for i, folder in enumerate(folders[:1]):
        print(f"Folder {i+1}/{len(folders)}")
        folder_path_full = os.path.join(folder_path, folder)

        for file_name in os.listdir(folder_path_full):
            if file_name.endswith('.txt') and not file_name.startswith('.'):
                file_path = os.path.join(folder_path_full, file_name)

                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    file_content = file.read()

                    # Split by the PokerStars Hand # line (more reliable)
                    hands = file_content.split('PokerStars Hand #')

                    # The first element will be the text before the first hand, discard it
                    hands = hands[1:] # Slice the list from index 1

                    # Add the "PokerStars Hand #" back to each hand
                    hands = ["PokerStars Hand #" + hand for hand in hands]

                    total_hands.extend(hands)

    return total_hands

if __name__ == '__main__':
    total_hands = get_total_hands()

    all_prompts = []

    # Assuming 'total_hands' contains a list of hand histories (strings)
    for hand in total_hands:
        if "SHOW DOWN" not in hand:
            continue

        currency = 'USD'
        blind_value = '0.50/1.00'

        small_blind = float(blind_value.split('/')[0])
        big_blind = float(blind_value.split('/')[1])

        # Extract showdown information
        showdown_pattern = r"([^\n]+): shows \[(.*?)\]"
        showdown_info = re.findall(showdown_pattern, hand)

        # Find the line containing "posts small blind"
        small_blind_pattern = r"([^\n]+) posts small blind \$(\d+\.\d+)"
        small_blind_match = re.search(small_blind_pattern, hand)

        if small_blind_match:
            small_blind_player = small_blind_match.group(1)
            small_blind_amount = float(small_blind_match.group(2))
            small_blind_line = small_blind_match.group(0)  # Get the whole line where small blind is posted
        else:
            continue  # Skip if no small blind post found

        # Create a dictionary to map player names to seat numbers
        players = re.findall(r"Seat (\d+): ([\s\S]+?) \(\$([0-9.]+) in chips\)(?:.*?(is sitting out))?", hand, re.MULTILINE)
        player_seat_map = {player[1]: f"Seat {player[0]}: {player[1]}" for player in players}

        # Prepare a list of players who are still in the game (not sitting out)
        playing_players = [
            seat for seat, name, chips, status in players if not status
        ]
        num_playing_players = len(playing_players)

        # Regex pattern to capture the seat number for the button
        button_pattern = r"Seat #(\d+) is the button"
        button_match = re.search(button_pattern, hand)

        if button_match:
            button_seat = f"Seat {button_match.group(1)}"  # Convert to 'Seat X' format
        else:
            button_seat = None  # Handle case where button info is missing

        player_order = get_player_order(button_seat, playing_players)

        # Now proceed with the showdown information and actions
        for player, cards_string in showdown_info:
            if len(cards_string) < 5:
                continue

            player_seat = None
            for seat, name, chips, status in players:
                if name == player:
                    player_seat = seat
                    break

            # Extract cards and player characteristics
            cards = cards_string.split()
            characteristics = []

            if closeness(cards[0], cards[1]):
                characteristics.append("close")

            if suitness(cards[0], cards[1]):
                characteristics.append("suit")

            if highness(cards[0], cards[1]):
                characteristics.append("high")

            # Extract all actions related to this player
            action_pattern = rf"({player}: .*)"
            actions = list(re.finditer(action_pattern, hand))

            for action in actions:
                if not any(word in action.group(1) for word in ['folds', 'raises', 'checks', 'bets', 'calls']):
                    continue

                action_start = action.start()  # Position of this action in the text

                # Get the action history from small blind posting until the action
                action_history = hand[small_blind_match.start():action_start].strip()

                # Replace stage names (HOLE CARDS, FLOP, TURN, RIVER) with the corresponding action stage names
                action_history = action_history.replace('*** HOLE CARDS ***', 'PREFLOP')\
                                 .replace('*** FLOP ***', 'FLOP')\
                                 .replace('*** TURN ***', 'TURN')\
                                 .replace('*** RIVER ***', 'RIVER')

                # Filter relevant lines (action-related lines only)
                keywords = ["PREFLOP", "FLOP", "TURN", "RIVER", "posts", "checks", "bets", "folds", "raises", "calls"]
                relevant_lines = [line for line in action_history.split('\n') if any(keyword in line for keyword in keywords)]
                action_history = '\n'.join(relevant_lines).strip()

                # Replace usernames with seat numbers in the action history
                for username, seat_info in player_seat_map.items():
                    # Explicitly escape special characters in username
                    escaped_username = re.escape(username)
                    seat_number = seat_info.split(':')[0].strip()  # Extract just the seat number

                    # Correct regex:  Lookbehind assertion and handle colon correctly
                    action_history = re.sub(rf"(?<!\S){escaped_username}(?=\s*:)", seat_number, action_history)

                # Debugging step to check updated action history

                # Find the most recent round (PREFLOP, FLOP, TURN, or RIVER) and the associated board
                last_round, last_board = get_last_round_and_board(action_history)

                # If no board is found, initialize it as an empty list
                if last_board is None:
                    last_board = []
                else:
                    last_board = last_board.split()

                # Get the best hand rank for this player
                highest_rank = best_hand(cards, last_board)

                # Initial stack sizes for each player
                initial_stacks = {f"Seat {seat}": float(chips) for seat, name, chips, status in players if str(seat) in playing_players}

                # Calculate the chips contributed by each player
                contributed_chips = get_pot_contributions(action_history)
                pot_size = sum(contributed_chips.values())

                # Calculate final stack sizes
                final_stacks = {
                    player: f"{round(initial_stacks[player] - contributed_chips.get(player, 0), 2):.2f}"
                    for player in initial_stacks
                }

                # Track player status (in or out of the hand)
                player_status = {'Seat ' + str(seat): 'in' for seat in playing_players}
                for seat in player_status:
                    if seat + ': folds' in action_history:  # Corrected check
                        player_status[seat] = 'out'

                # Determine legal moves for the current player
                legal_moves = get_legal_moves(action_history)
                current_bet = get_current_bet(action_history, blind_value)

                # Calculate the player's contribution for the final bet
                player_contribution = get_player_contribution(parse_hand_history(action_history)[-1], "Seat " + str(player_seat))

                # Potential bet sizes for the current round
                potential_bets_and_raises = [
                    round(0.1 * pot_size, 2), round(0.2 * pot_size, 2), round(0.3 * pot_size, 2), round(0.4 * pot_size, 2),
                    round(0.5 * pot_size, 2), round(0.75 * pot_size, 2), round(pot_size, 2), round(1.25 * pot_size, 2),
                    round(1.5 * pot_size, 2), round(2 * pot_size, 2), round(2.5 * pot_size, 2), round(3 * pot_size, 2),
                    round(4 * pot_size, 2), round(5 * pot_size, 2), float(final_stacks["Seat " + str(player_seat)])
                ]

                # Filter possible bets based on the current bet size and final stack
                potential_bets_and_raises = [bet for bet in potential_bets_and_raises if current_bet < bet and bet - player_contribution <= float(final_stacks["Seat " + str(player_seat)])]

                if len(potential_bets_and_raises) == 0:
                    # Remove 'raise' or 'bet' options if the list is empty
                    legal_moves = [move for move in legal_moves if move not in ['raise', 'bet']]

                info = {"num_playing_players": num_playing_players, "currency": currency, 'blind_value': blind_value, 'player_order': player_order, 'button_seat': button_seat.replace("Seat ",''), 'cards': cards, 'characteristics': characteristics, 'player_seat': player_seat, "players": players,
                          "action_history": action_history, "last_round": last_round, 'last_board': last_board, "Rank": highest_rank, 'pot_value': pot_size,
                          "player_status": player_status, 'final_stacks': final_stacks,
                          "player_contribution": player_contribution, "current_bet": current_bet, "legal_moves": legal_moves, "potential_bets_and_raises": potential_bets_and_raises
                        }
                #
                # print(construct_prompt(info))
                # print(player_contribution)
                # print('\n-----------------------------\n')
                import re

                pattern = r": (raises|bets|calls|checks|folds)(?: \$([\d\.]+))?"

                matches = re.findall(pattern, action.group(1))
                # correct_move = [(action, amount if amount else "n/a") for action, amount in matches]

                print(matches)

                # print(action)

                all_prompts.append(construct_prompt(info))

    random.shuffle(all_prompts)


    dataset = [{"prompt": "User:\n" + prompt + "\n\nAssistant:"} for prompt in all_prompts[:1000]]
    with open("prompt_dataset_RLHF.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=4)


    #
    # output_file = "prompts_and_hands.txt"
    #
    # # Check if the file exists, if not create it.
    # if not os.path.exists(outpPut_file):
    #     with open(output_file, "w") as f:
    #         f.write("Prompts and Hands:\n\n")  # Add a header
    #
    # for (prompt, hand) in all_prompts[:5]:
    #     with open(output_file, "a") as f:  # Open in append mode ("a")
    #         f.write(f"Prompt:\n{prompt}\n\n")
    #         f.write(f"Hand:\n{hand}\n\n")
    #         f.write("\n------------------------\n\n")