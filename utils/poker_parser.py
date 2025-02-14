import re
from utils.get_card_data import closeness, highness, suitness
from utils.get_hand_data import best_hand
from collections import defaultdict

def get_last_round_and_board(hand_history: str):
    # Define regex patterns for rounds and boards
    rounds = ['PREFLOP', 'FLOP', 'TURN', 'RIVER']
    board_pattern = r'\[([^\]]+)\]'  # Pattern to capture cards inside brackets

    # Initialize variables
    last_round = None
    last_board = None

    # Split the hand history into lines
    lines = hand_history.split('\n')

    # Iterate over the lines to find the last round and board
    for line in lines:
        # Check for exact match of round names
        for round_name in rounds:
            if line.startswith(round_name):  # Match exact round name
                last_round = round_name
                # Find all boards associated with the round (cards in brackets)
                boards = re.findall(board_pattern, line)
                if boards:
                    if last_round in ['TURN', 'RIVER'] and len(boards) == 2:
                        # For TURN and RIVER, take the first set of cards and the extra card
                        last_board = ' '.join(boards)  # Join the boards together (main and extra card)
                    else:
                        # For PREFLOP and FLOP, just take the first set of cards
                        last_board = boards[0]

    # Return the result
    return last_round, last_board

def parse_hand_history(hand_history):
    rounds = []
    current_round = []

    # Define round headers to detect different rounds
    round_headers = ["PREFLOP", "FLOP", "TURN", "RIVER"]

    # Iterate through each line of the hand history
    for line in hand_history.strip().split("\n"):
        # Check if the line contains a round header
        if any(round_header in line for round_header in round_headers):
            # If we have accumulated any action in the current round, store it
            if current_round:
                rounds.append(current_round)
            # Start a new round with the current line
            current_round = [line]
        else:
            # Otherwise, continue accumulating lines for the current round
            current_round.append(line)

    # Don't forget to add the last round
    if current_round:
        rounds.append(current_round)

    return rounds


# Function to get the contribution of one player in a round
def get_player_contribution(round_actions, player):
    contribution = 0.0

    for line in round_actions:
        # Detect posting blinds (small blind / big blind)
        post_match = re.match(r"(.+): posts (small blind|big blind) \$?([\d\.]+)", line)
        if post_match and post_match.group(1) == player:
            contribution += float(post_match.group(3))

        # Detect bets and calls
        bet_or_call_match = re.match(r"(.+): (bets|calls) \$?([\d\.]+)", line)
        if bet_or_call_match and bet_or_call_match.group(1) == player:
            contribution += float(bet_or_call_match.group(3))

        # Detect raises (track the total raise amount, not just the increase)
        raise_match = re.match(r"(.+): raises \$?([\d\.]+) to \$?([\d\.]+)", line)
        if raise_match and raise_match.group(1) == player:
            contribution = float(raise_match.group(3))  # Set to the total raised amount

    return contribution  # Return the final contribution for this player in the round

# Function to get the total contributions of all players across all rounds
def get_pot_contributions(hand_history):
    rounds = parse_hand_history(hand_history)  # Assuming your parse_hand_history function is correctly working
    contributions = defaultdict(float)

    for round_actions in rounds:
        # For each round, calculate the contribution of every player
        players_in_round = {line.split(":")[0] for line in round_actions if 'Seat' in line}  # Extract all seat numbers

        for player in players_in_round:
            contributions[player] += get_player_contribution(round_actions, player)

    return dict(contributions)  # Return the final contribution dictionary for all players

def get_legal_moves(action_history):
    split_rounds = parse_hand_history(action_history)

    current_round_actions = split_rounds[-1]

    round_headers = ["PREFLOP", "FLOP", "TURN", "RIVER"]
    current_round_actions = [action for action in current_round_actions if not any(header in action for header in round_headers)]

    current_round_actions = [action for action in current_round_actions if "folds" not in action]

    # Now analyze the current round actions
    if len(current_round_actions) == 0:
        # If no actions have been taken in the current round, we can check or bet

        return ["check", "bet"]

    last_nonfolding_action = current_round_actions[-1]

    # Determine legal moves based on the last nonfolding action
    if last_nonfolding_action:
        if "raises" in last_nonfolding_action or "bets" in last_nonfolding_action or "posts" in last_nonfolding_action or "calls" in last_nonfolding_action:
            # Last action was a bet or raise: options are call, raise, fold
            return ["call", "raise", "fold"]
        elif "checks" in last_nonfolding_action:
            # Last action was a check: options are check, bet
            return ["check", "bet"]

def get_current_bet(hand_history, blind_value):
    rounds = parse_hand_history(hand_history)
    current_round = rounds[-1]
    round_history = "\n".join(current_round)

    raise_pattern = r"(\S+) raises \$(\d+(?:\.\d+)?) to \$(\d+(?:\.\d+)?)" # Improved regex
    bet_pattern = r"(\S+) bets \$(\d+(?:\.\d+)?)" # Improved regex

    raise_actions = re.findall(raise_pattern, round_history)

    if raise_actions:
        return float(raise_actions[-1][2])

    bet_actions = re.findall(bet_pattern, round_history)

    if bet_actions:
        return float(bet_actions[-1][1])

    if current_round[0]=='PREFLOP':
        return float(blind_value.split('/')[1])

    return 0.0

def get_player_order(button_seat, playing_players):
    """
    Returns the order in which players act based on the button position.
    """
    if button_seat is None:
        return playing_players  # Fallback to default order if no button is found

    # Sort the players in order of action starting from the small blind
    sorted_players = sorted(playing_players, key=lambda seat: (seat < button_seat, seat))
    return sorted_players

def construct_prompt(info):
    prompt = 'You are an experienced gambler. Now you need to assist me to make decisions in Texas Hold’em games. You have been provided with a series of observable information:\n\n'
    prompt += f"Player Amount: [{str(info['num_playing_players'])}], Currency: [{info['currency']}], Blind Value: [{info['blind_value']}], Order: {repr(info['player_order'])}, Seat {str(info['button_seat'])} is button.\n\n"
    prompt += f"My Cards: {repr(info['cards'])}, the characteristics of my cards: {repr(info['characteristics'])}, My Seat: {str(info['player_seat'])}\n\n"

    # # Add a line for each player with their seat and chip count
    # for seat, name, chips, status in info['players']:
    #     prompt += f"Seat {seat} has {chips} in chips to start the round.\n"

    prompt += "Action History:\n"

    prompt += info['action_history']

    prompt += f"\n\nCurrent Stage: ['{info['last_round']}'], Public cards: {repr(info['last_board'])}, Pot Value: [{info['pot_value']:,.2f}], Current hand strength: ['{info['Rank']}']\n\n"

    for player, activity in info['player_status'].items():
      if activity == 'in':
        prompt += f"{player} is still in game with ${info['final_stacks'][player]} in chips.\n"
      else:
        prompt += f"{player} is not in game.\n"

    prompt+='\n'

    if "call" in info['legal_moves']:
        prompt += f"It costs ${'{:.2f}'.format(info['current_bet'] - info['player_contribution'])} to call here."
    if info['current_bet'] - info['player_contribution'] > float(info['final_stacks']["Seat " + str(info["player_seat"])]):
        prompt += f" NOTE: To call requires going all-in, as the call amount is higher than your chip count."

    # Now construct the prompt based on the filtered legal_moves
    prompt += "\n\nFrom the following actions, what should I do?: " + str(info['legal_moves']) + '.'

    if "raise" in info['legal_moves'] or "bet" in info['legal_moves']:
        prompt += " If you chose 'bet' or 'raise', what should I bet/raise to? Choose from the following options: "
        prompt += str(info['potential_bets_and_raises'])[:-1] + ' (all-in)].'

    prompt += "\n\n"

    prompt+="For clarity, all chip stacks and the pot size are calculated using the current round's actions. So if during this round, a player bet $50, that is immediately added to the pot."

    prompt+='Write a 4-6 sentence long analysis before making your decision explaining exactly why you chose that option, using information such as opponents’ ranges, proper poker strategy, and other things.'

    prompt+="\n\nAt the end of the analysis, put your answer as follows: [*choice* (bet/raise/check/call/fold), *amount*]. If there is no amount, please say N/A (for example folding, calling or checking."

    prompt += '\n\nExample Output:\n"\n'

    prompt += 'You are in Seat 2 holding [Th, Ah], which gives you an Ace-high and a flush draw. The public cards are [\'Kh\', \'7h\', \'2s\', \'5d\']. The pot is currently 0.17, and Seat 9 just raised 0.05 to 0.1. Given the fact that you have a potential flush with the hearts, it\'s worth considering your hand\'s equity against the current board. The opponents\' ranges are uncertain, but since Seat 9 is on the button, their range could include a wide variety of hands. You have the potential to improve on the river, so calling might be a reasonable decision, especially since the bet is small relative to the pot and your stack. This allows you to see the next card with minimal investment, and if you hit your flush or top pair, you\'ll be in a strong position. \n\n[call, N/A]\n"'


    return prompt

# with open("all_prompts.txt", "w") as f:  # Open file in write mode ("w")
#     for prompt in all_prompts:
#         f.write(prompt + "\n-----------------------------\n")  # Write all prompts at once

# # Example usage:
# loaded_prompts = load_and_split_prompts("all_prompts.txt")
#
# from openai import OpenAI
# client = OpenAI(api_key="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")
#
# chat_completion = client.chat.completions.create(
#     messages=[
#         {
#             "role": "user",
#             "content": loaded_prompts[0],
#         }
#     ],
#     model="gpt-4o",
# )
#
