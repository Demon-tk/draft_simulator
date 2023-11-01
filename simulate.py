import pandas as pd


class SnakeDraft:
    positions = ['qb', 'rb', 'rb', 'wr', 'wr', 'wr', 'te', 'flex']
    draft_count = dict.fromkeys(positions, 0)
    team = []

    def __init__(self, file):
        self.data = pd.read_csv(file)
        self.handle_adp()
        self.ranked_data = self.rank_players()

    def rank_players(self):
        self.data = self.data.copy()
        self.data['Position'] = self.data['Position Rank'].apply(lambda x: x.split('-')[0].lower())
        pos_counts = self.data['Position'].value_counts()
        self.data['Scarcity'] = self.data['Position'].apply(lambda x: 1 / pos_counts[x])
        self.data['Value Over Replacement'] = self.data['FF Pts'] * self.data['Scarcity']
        self.data.sort_values(by=['Value Over Replacement', 'ADP'], ascending=[False, True], inplace=True)
        return self.data

    def select_player(self, round):
        for _, row in self.ranked_data.iterrows():
            position = row['Position']
            if position in self.positions and self.draft_count[position] < self.positions.count(position):
                if row['ADP'] <= round * 6:  # Assuming each round is 10 picks
                    self.draft_count[position] += 1
                    self.team.append(row['Player'])
                    self.ranked_data = self.ranked_data[self.ranked_data['Player'] != row['Player']]
                    break

    def perform_draft(self):
        for i in range(8):
            self.select_player(i + 1)
        return self.team

    def handle_adp(self):
        def convert_adp(adp):
            if adp == '--':
                return 201
            round, pick = adp.split('.')
            return (int(round) - 1) * 6 + int(pick)

        self.data['ADP'] = self.data['ADP'].apply(convert_adp)


if __name__ == "__main__":
    draft = SnakeDraft('4for4-full-impact-xfactor-142240-table.csv')
    print(draft.perform_draft())
