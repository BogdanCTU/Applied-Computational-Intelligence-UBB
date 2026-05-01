import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

class AuctionDataVisualizer:
    """
    Processes Vickrey auction data and generates 30 distinct visualizations.
    """

    def __init__(self, file_path: str, output_directory: str = "plots"):
        """
        Initializes the instance with the input file path and output directory.
        """
        self.file_path = file_path
        self.output_directory = output_directory
        self.data = pd.DataFrame()
        self.players = [
            "truthful_P1",
            "random_reasonable_P2",
            "underbid_bayesian_P3",
            "overbid_P4",
            "noisybr_P5"
        ]

    def load_data(self) -> None:
        """
        Reads data from the specified CSV file and creates the output directory if it does not exist.
        """
        self.data = pd.read_csv(self.file_path)
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)

    def generate_trueval_vs_bid_plots(self) -> None:
        """
        Generates individual line plots comparing True Value and Bid for each player across rounds.
        Creates plots 1 through 5.
        """
        for i, player in enumerate(self.players, start=1):
            plt.figure(figsize=(8, 5))
            plt.plot(self.data['Round'], self.data[f'{player}_TrueVal'], marker='o', label='True Value')
            plt.plot(self.data['Round'], self.data[f'{player}_Bid'], marker='x', label='Bid')
            plt.title(f'{player}: True Value vs Bid')
            plt.xlabel('Round')
            plt.ylabel('Amount')
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_directory, f'plot_{i}.png'))
            plt.close()

    def generate_profit_per_round_plots(self) -> None:
        """
        Generates individual bar charts displaying the profit earned per round for each player.
        Creates plots 6 through 10.
        """
        for i, player in enumerate(self.players, start=6):
            plt.figure(figsize=(8, 5))
            plt.bar(self.data['Round'], self.data[f'{player}_Profit'], color='skyblue')
            plt.title(f'{player}: Profit per Round')
            plt.xlabel('Round')
            plt.ylabel('Profit')
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_directory, f'plot_{i}.png'))
            plt.close()

    def generate_total_profit_progression_plots(self) -> None:
        """
        Generates individual line plots illustrating the cumulative total profit for each player over rounds.
        Creates plots 11 through 15.
        """
        for i, player in enumerate(self.players, start=11):
            plt.figure(figsize=(8, 5))
            plt.plot(self.data['Round'], self.data[f'{player}_TotalProfit'], marker='s', color='green')
            plt.title(f'{player}: Total Profit Progression')
            plt.xlabel('Round')
            plt.ylabel('Total Profit')
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_directory, f'plot_{i}.png'))
            plt.close()

    def generate_auction_metrics_plots(self) -> None:
        """
        Generates plots for general auction metrics including winning bids, second prices, and winner frequencies.
        Creates plots 16 through 21.
        """
        # Plot 16: Winning Bid over Rounds
        plt.figure(figsize=(8, 5))
        plt.plot(self.data['Round'], self.data['Winning_Bid'], marker='o', color='purple')
        plt.title('Winning Bid over Rounds')
        plt.xlabel('Round')
        plt.ylabel('Winning Bid')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_directory, 'plot_16.png'))
        plt.close()

        # Plot 17: Second Price over Rounds
        plt.figure(figsize=(8, 5))
        plt.plot(self.data['Round'], self.data['Second_Price'], marker='o', color='orange')
        plt.title('Second Price over Rounds')
        plt.xlabel('Round')
        plt.ylabel('Second Price')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_directory, 'plot_17.png'))
        plt.close()

        # Plot 18: Winning Bid vs Second Price
        plt.figure(figsize=(8, 5))
        plt.plot(self.data['Round'], self.data['Winning_Bid'], label='Winning Bid', marker='o')
        plt.plot(self.data['Round'], self.data['Second_Price'], label='Second Price', marker='x')
        plt.title('Winning Bid vs Second Price')
        plt.xlabel('Round')
        plt.ylabel('Amount')
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_directory, 'plot_18.png'))
        plt.close()

        # Plot 19: Winner Frequency
        plt.figure(figsize=(8, 5))
        winner_counts = self.data['Winner_ID'].value_counts().sort_index()
        winner_counts.plot(kind='bar', color='teal')
        plt.title('Winner Frequency')
        plt.xlabel('Player ID')
        plt.ylabel('Number of Wins')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_directory, 'plot_19.png'))
        plt.close()

        # Plot 20: Distribution of Winning Bids
        plt.figure(figsize=(8, 5))
        sns.histplot(self.data['Winning_Bid'], kde=True, color='purple', bins=10)
        plt.title('Distribution of Winning Bids')
        plt.xlabel('Winning Bid')
        plt.ylabel('Frequency')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_directory, 'plot_20.png'))
        plt.close()

        # Plot 21: Distribution of Second Prices
        plt.figure(figsize=(8, 5))
        sns.histplot(self.data['Second_Price'], kde=True, color='orange', bins=10)
        plt.title('Distribution of Second Prices')
        plt.xlabel('Second Price')
        plt.ylabel('Frequency')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_directory, 'plot_21.png'))
        plt.close()

    def generate_trueval_distribution_plots(self) -> None:
        """
        Generates individual histograms representing the distribution of True Values for each player.
        Creates plots 22 through 26.
        """
        for i, player in enumerate(self.players, start=22):
            plt.figure(figsize=(8, 5))
            sns.histplot(self.data[f'{player}_TrueVal'], kde=True, bins=10)
            plt.title(f'{player}: True Value Distribution')
            plt.xlabel('True Value')
            plt.ylabel('Frequency')
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_directory, f'plot_{i}.png'))
            plt.close()

    def generate_summary_comparison_plots(self) -> None:
        """
        Generates summary comparison plots across all players and rounds.
        Creates plots 27 through 30.
        """
        # Plot 27: All Players Total Profit at Final Round
        final_round = self.data.iloc[-1]
        total_profits = [final_round[f'{p}_TotalProfit'] for p in self.players]
        plt.figure(figsize=(10, 6))
        plt.bar(self.players, total_profits, color='coral')
        plt.title('Final Total Profit Comparison')
        plt.xlabel('Player')
        plt.ylabel('Total Profit')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_directory, 'plot_27.png'))
        plt.close()

        # Plot 28: Spread (Winning Bid - Second Price)
        spread = self.data['Winning_Bid'] - self.data['Second_Price']
        plt.figure(figsize=(8, 5))
        plt.plot(self.data['Round'], spread, marker='d', color='maroon')
        plt.title('Spread (Winning Bid - Second Price) over Rounds')
        plt.xlabel('Round')
        plt.ylabel('Spread')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_directory, 'plot_28.png'))
        plt.close()

        # Plot 29: Total Bid Count Comparison (Sum of all bids)
        total_bids = [self.data[f'{p}_Bid'].sum() for p in self.players]
        plt.figure(figsize=(10, 6))
        plt.bar(self.players, total_bids, color='indigo')
        plt.title('Sum of All Bids per Player')
        plt.xlabel('Player')
        plt.ylabel('Total Bid Amount')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_directory, 'plot_29.png'))
        plt.close()

        # Plot 30: All Players Total Profit Progression Comparison
        plt.figure(figsize=(10, 6))
        for player in self.players:
            plt.plot(self.data['Round'], self.data[f'{player}_TotalProfit'], marker='o', label=player)
        plt.title('Total Profit Progression Comparison')
        plt.xlabel('Round')
        plt.ylabel('Total Profit')
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_directory, 'plot_30.png'))
        plt.close()

    def generate_all_plots(self) -> None:
        """
        Executes all plotting methods to generate the full set of 30 plots.
        """
        self.generate_trueval_vs_bid_plots()
        self.generate_profit_per_round_plots()
        self.generate_total_profit_progression_plots()
        self.generate_auction_metrics_plots()
        self.generate_trueval_distribution_plots()
        self.generate_summary_comparison_plots()


if __name__ == "__main__":
    visualizer = AuctionDataVisualizer("vickrey_auction_results.csv")
    visualizer.load_data()
    visualizer.generate_all_plots()
