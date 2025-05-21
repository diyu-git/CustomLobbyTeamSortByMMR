import os
import json
import argparse
from itertools import combinations
import logging

"""
MIT License

Copyright (c) 2025 Diyu of Sirocco Gaming Community (Lunchbox Entertainment)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

DISCLAIMER: The author is not obligated to provide updates, fixes, or support for this software. The software is provided 
"as-is" without any warranties.
"""

logging.basicConfig(level=logging.INFO,format="%(message)s")

def find_latest_log_folder(log_base_directory):
    try:
        folders = [f for f in os.listdir(log_base_directory) if os.path.isdir(os.path.join(log_base_directory, f))]
        return max(folders, key=lambda f: os.path.getctime(os.path.join(log_base_directory, f)))
    except ValueError:
        logging.error("No valid log folders found.")
        return None

def read_log_file(file_path):
    try:
        with open(file_path, 'r') as file:
            # Extract relevant lines containing "Parsed session message" and "customGameNotification"
            relevant_lines = [
                line.split(': ', 1)[1]
                for line in file
                if '[BACKEND] Parsed session message:' in line and '"customGameNotification"' in line
            ]
            if relevant_lines:
                return relevant_lines[-1]  # Return the last matching line
            raise ValueError("No matching 'customGameNotification' entries found in the log file.")
    except (OSError, IndexError) as error:
        logging.error(f"Error reading log file: {error}")
        return None
    except ValueError as error:
        logging.error(error)
        raise

def find_last_parsed_session_message(log_directory):
    log_file_path = os.path.join(log_directory, "Full_Log.log")
    return read_log_file(log_file_path)

def process_players(players_data):
    return [{'displayName': player['displayName'], 'mmr': player['mmr']} for player in players_data]

def extract_player_info(session_message_data):
    return process_players(session_message_data['notification']['customGameNotification']['customGameEvent']['lobby']['players'])

def initial_team_assignment(sorted_players):
    total_mmr = sum(player['mmr'] for player in sorted_players)
    results = []

    for combo in combinations(range(len(sorted_players)), len(sorted_players) // 2):
        team_a = [sorted_players[i] for i in combo]
        team_a_mmr_total = sum(player['mmr'] for player in team_a)
        team_b_mmr_total = total_mmr - team_a_mmr_total
        results.append((team_a, abs(team_a_mmr_total - team_b_mmr_total)))

    # Sort by MMR difference
    results.sort(key=lambda x: x[1])

    # Get the best team
    team_a, diff = results[0]
    team_b = [player for player in sorted_players if player not in team_a]
    logging.info(f"Found optimal team assignment with MMR difference of {diff}")

    return team_a, team_b

def sort_into_teams(player_lobby_info):
    sorted_players = sorted(player_lobby_info, key=lambda x: x['mmr'], reverse=True)

    team_a, team_b = initial_team_assignment(sorted_players)

    avg_mmr_team_a = sum(player['mmr'] for player in team_a) // len(team_a) if team_a else 0
    avg_mmr_team_b = sum(player['mmr'] for player in team_b) // len(team_b) if team_b else 0

    return team_a, team_b, avg_mmr_team_a, avg_mmr_team_b

def print_team_details(team_name, avg_mmr, team):
    logging.info(
        f"\n{team_name} - Avg MMR: {avg_mmr}\n" +
        "-" * 40 + "\n" +
        "\n".join(f"{player['displayName']:<20} | MMR: {player['mmr']:<5}" for player in team) +
        "\n" + "-" * 40
    )

def print_teams(team_a, team_b, avg_mmr_team_a, avg_mmr_team_b):
    print_team_details("Team A", avg_mmr_team_a, team_a)
    print_team_details("Team B", avg_mmr_team_b, team_b)

def main():
    parser = argparse.ArgumentParser(description="Parse log file and sort players into teams.")
    parser.add_argument("log_game_directory_name", type=str, nargs='?', default="latest", help="Directory name for lobby logs.")
    args = parser.parse_args()

    local_low_path = os.path.join(os.getenv('LOCALAPPDATA').replace('Local', 'LocalLow'), 'LunchboxEntertainment', 'Sirocco', 'Logs')
    log_game_directory_name = find_latest_log_folder(local_low_path) if args.log_game_directory_name == "latest" else args.log_game_directory_name

    if not log_game_directory_name or not os.path.isdir(os.path.join(local_low_path, log_game_directory_name)):
        logging.error(f"Invalid log directory: {log_game_directory_name}")
        return

    log_game_directory = os.path.join(local_low_path, log_game_directory_name)
    logging.info(f"Processing log folder: {log_game_directory_name}")

    try:
        parsed_message = find_last_parsed_session_message(log_game_directory)
        if not parsed_message:
            logging.error("No valid session message was found.")
            return

        parsed_message_json = json.loads(parsed_message)
        players_info = extract_player_info(parsed_message_json)
        if not players_info:
            logging.error("No players found in the session message.")
            return

        print_teams(*sort_into_teams(players_info))

    except json.JSONDecodeError as json_error:
        logging.error(f"Failed to parse JSON data: {json_error}")

if __name__ == "__main__":
    main()