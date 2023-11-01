import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from multiprocessing import Pool
import multiprocessing
import secrets

RANDOMNESS = 5


class Team:

    def __init__(self, number):
        self.players = []
        self.positions = {'QB': [], 'RB': [], 'WR': [], 'TE': [], 'FLEX': []}
        self.needs = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 1, 'FLEX': 1}
        self.total_relative_value = 0
        self.total_ff_pts = 0
        self.number = number
        self.pick_count = {}

    def add_player(self, player):
        position = player['Position Rank'].split('-')[0]

        if self.needs[position] > 0:
            self.positions[position].append(player)
            self.needs[position] -= 1
        else:
            if self.needs['FLEX'] > 0:
                self.positions['FLEX'].append(player)
                self.needs['FLEX'] -= 1

        self.players.append(player)
        self.total_relative_value += player['Relative Value']
        self.total_ff_pts += player['FF Pts']

        if player['Player'] in self.pick_count:
            self.pick_count[player['Player']] += 1
        else:
            self.pick_count[player['Player']] = 1

    def needed_positions(self):
        needed_positions = [pos for pos, count in self.needs.items() if count > 0]
        if 'FLEX' in needed_positions:
            needed_positions.remove('FLEX')
            flex_positions = ["RB", "WR", "TE"]
            count_dict = {pos: len(self.positions[pos]) for pos in flex_positions}
            sorted_counts = sorted(count_dict.items(), key=lambda item: item[1])
            for pos, _ in sorted_counts:
                if self.needs[pos] != 0:
                    needed_positions.append(pos)
                    break
        return needed_positions

    def has_player(self, player):
        return player in self.players

    def team_info(self):
        return f'Team {self.number} - Total FF Pts: {self.total_ff_pts}, Total Relative Value: {self.total_relative_value}\n'


class DraftConstraints:

    def __init__(self, simulation_num, player_data, total_teams=10):
        self.simulation_num = simulation_num
        self.player_data = player_data
        self.teams = [Team(i + 1) for i in range(total_teams)]
        self.player_frequencies = {}

    def run_draft(self):
        potential_freq_teams = []
        for i in range(8):
            draft_order = self.teams if i % 2 == 0 else reversed(self.teams)
            for team in draft_order:
                remaining = self.player_data[~self.player_data['Player'].isin(
                    [player for Team in self.teams for player in Team.players])]
                remaining.sort_values(by=['Relative Value', 'FF Pts'], ascending=False, inplace=True)
                best_player = self._select_best_player(remaining, team, team.number == 10)
                team.add_player(best_player)
                self.player_data = self.player_data[self.player_data['Player'] != best_player['Player']]
                #print(f"Team {team.number} picked {best_player['Player']}")

        # Checking the constraint and storing teams which satisfies the constraints
        max_relative_value = max([team.total_relative_value for team in self.teams])
        max_ff_pts = max([team.total_ff_pts for team in self.teams])
        for team in self.teams:
            if team.number == 10 and team.total_relative_value == max_relative_value and team.total_ff_pts == max_ff_pts:
                potential_freq_teams.append(team)

        # Updating player frequencies based on constraint satisfied teams
        for team in potential_freq_teams:
            for player, count in team.pick_count.items():
                if player in self.player_frequencies:
                    self.player_frequencies[player] += count
                else:
                    self.player_frequencies[player] = count

        # print("=== Summary of the Draft ===")
        # for team in sorted(self.teams, key=lambda x: x.total_ff_pts, reverse=True):
        #     print(team.team_info())

    def _select_best_player(self, remaining, team, is_me=False):
        positions_needed = team.needed_positions()

        if not is_me:
            positional_players = remaining[
                remaining['Position Rank'].apply(lambda x: x.split('-')[0]).isin(positions_needed)]
            positional_players = positional_players.sort_values(by='ADP')

            secretsGenerator = secrets.SystemRandom()
            adp_random = secretsGenerator.randint(0, RANDOMNESS)

            if len(positional_players) <= adp_random:
                adp_switch = 0
            else:
                adp_switch = adp_random

            if not positional_players.empty:
                return positional_players.iloc[adp_switch]

        else:
            num_picks_until_my_turn = 20 - ((team.number) % len(self.teams)) * 2
            potential_picks = remaining.sort_values(by='ADP').head(num_picks_until_my_turn)
            potential_picks = potential_picks.sort_values(by="Relative Value", ascending=False)

            for _, player in potential_picks.iterrows():
                position = player['Position Rank'].split('-')[0]
                if position in positions_needed:
                    return player

            # If no player is found with the needed positions, find the player with the highest relative value for the needed positions
            for position in positions_needed:
                potential_position_picks = remaining[
                    remaining['Position Rank'].apply(lambda x: x.split('-')[0]) == position]
                if not potential_position_picks.empty:
                    best_player = potential_position_picks.iloc[0]
                    return best_player

        return remaining.iloc[0]


def run_simulation(args):
    i, player_info = args
    print(f"\nSimulation #{i + 1}")
    constraints = DraftConstraints(i, player_info.copy())
    constraints.run_draft()

    return constraints


if __name__ == "__main__":
    player_info = pd.read_csv('4for4-full-impact-xfactor-183972-table.csv')
    player_info['ADP'] = player_info['ADP'].apply(
        lambda adp: int(adp.split('.')[0]) * 10 + int(adp.split('.')[1]) if adp != '--' else 201)

    num_sims = 10000
    draft_constraints = []

    # Use multiprocessing to run draft simulations in parallel
    with Pool(processes=multiprocessing.cpu_count()) as pool:
        draft_constraints = pool.map(run_simulation, [(i, player_info) for i in range(num_sims)])

    pickup_frequencies_constraints = {}
    player_picked_counts = {}

    # Gathering the pick counts
    for constraints in draft_constraints:
        for player, count in constraints.player_frequencies.items():
            if player in player_picked_counts:
                player_picked_counts[player] += count
            else:
                player_picked_counts[player] = count

    # Calculating the pick percentages of the players
    player_pick_percentages = {player: picked_count / num_sims for player, picked_count in player_picked_counts.items()}

    # Get top 10 players
    best_players = sorted(player_pick_percentages.items(), key=lambda item: item[1], reverse=True)[:20]

    players = [player[0] for player in best_players]
    percentages = [player[1] for player in best_players]

    plt.figure(figsize=(12, 8))
    plt.barh(players, percentages, color='blue')
    plt.xlabel("Pick Percentage")
    plt.title(f"Player Pick Percentages for {num_sims} Simulations using {RANDOMNESS} pick deviation")
    plt.gca().invert_yaxis()  # reverse the order of players
    plt.tight_layout()
    plt.show()
