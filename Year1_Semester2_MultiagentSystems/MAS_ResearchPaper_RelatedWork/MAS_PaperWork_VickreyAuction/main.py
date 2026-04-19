import asyncio
import json
import random
import logging
import sys
import statistics
import pandas as pd
import platform
import uuid
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

# ================= LOGGING =================
logger = logging.getLogger("vickrey_simulation")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)

logging.getLogger("spade").setLevel(logging.WARNING)
logging.getLogger("slixmpp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# ================= PARAMETERS =================
ROUNDS = 100
XMPP_DOMAIN = "localhost"
XMPP_HOST = "127.0.0.1"
XMPP_PORT = 5222
PASSWORD = "admin"

class StrategySelector:
    """
    Provides a curated list of strategies for the Vickrey Auction simulation.
    """

    @staticmethod
    def get_selected_strategies() -> list[str]:
        """
        Returns a list of exactly twenty specific strategy identifiers.
        
        Returns:
            list[str]: A list of strategy names formatted for the simulation environment.
        """
        return [
            "truthful",              # Bids exact true valuation. (Dominant strategy)
            "random",                # Bids a random amount between 0 and 200.
            "always_zero",           # Always bids 0.
            "always_max",            # Always bids maximum possible value (200).
            "underbid_10_percent",   # Bids 90% of true valuation.
            "overbid_10_percent",    # Bids 110% of true valuation.
            "underbid_fixed_10",     # Bids exactly 10 units below true valuation.
            "overbid_fixed_10",      # Bids exactly 10 units above true valuation.
            "imitate_last_winner",   # Copies the winning bid from the previous round.
            "average_past_winners",  # Calculates the average of all past winning bids.
            "adaptive_increase",     # Increases bid by 20% if the previous round was lost.
            "adaptive_decrease",     # Decreases bid by 20% if the previous round was won.
            "spiteful",              # Bids 150% of true valuation to force others to pay more.
            "timid",                 # Bids 50% of true valuation to avoid overpaying.
            "epsilon_greedy",        # Bids truthfully 90% of the time, and randomly 10% of the time.
            "trend_follower",        # Adjusts bid based on the difference between the last two winning bids.
            "memory_3_avg",          # Averages the agent's own last three bids.
            "competitor_aware",      # Adds 5 units to the true valuation if another agent won last time.
            "win_stay_lose_shift",   # Bids truthfully if winning, but bids randomly if losing.
            "strategy_switcher"      # Switches from truthful to overbidding if the win rate drops too low.
        ]

# ================= PLAYER AGENT =================
class BidderAgent(Agent):
    """
    Represents an independent bidder in the auction.
    Maintains historical state and executes a specific bidding strategy.
    """
    def __init__(self, jid, password, player_id, strategy):
        """
        Initializes the bidder agent with identification and strategy parameters.
        
        Args:
            jid (str): The Jabber ID for XMPP communication.
            password (str): The password for the XMPP server.
            player_id (int): The unique numerical identifier for the player.
            strategy (str): The name of the decision-making logic the agent utilizes.
        """
        super().__init__(jid, password)
        self.player_id = player_id
        self.strategy = strategy
        
        self.history_winning_bids = []
        self.history_my_bids = []
        self.won_last_round = False
        self.win_count = 0
        self.round_count = 0

    def calculate_bid(self, true_val: float) -> float:
        """
        Executes the assigned behavioral strategy to determine the bid amount.
        
        Args:
            true_val (float): The private, actual value the item holds for the agent this round.
            
        Returns:
            float: The calculated bid amount.
        """
        bid = true_val 

        if self.strategy == "truthful":
            bid = true_val

        elif self.strategy == "random":
            bid = random.uniform(0, 200)

        elif self.strategy == "always_zero":
            bid = 0.0

        elif self.strategy == "always_max":
            bid = 200.0

        elif self.strategy == "underbid_10_percent":
            bid = true_val * 0.90

        elif self.strategy == "overbid_10_percent":
            bid = true_val * 1.10

        elif self.strategy == "underbid_fixed_10":
            bid = max(0.0, true_val - 10.0)

        elif self.strategy == "overbid_fixed_10":
            bid = true_val + 10.0

        elif self.strategy == "imitate_last_winner":
            if self.history_winning_bids:
                bid = self.history_winning_bids[-1]
            else:
                bid = true_val

        elif self.strategy == "average_past_winners":
            if self.history_winning_bids:
                bid = sum(self.history_winning_bids) / len(self.history_winning_bids)
            else:
                bid = true_val

        elif self.strategy == "adaptive_increase":
            if self.round_count > 0 and not self.won_last_round:
                bid = true_val * 1.20
            else:
                bid = true_val

        elif self.strategy == "adaptive_decrease":
            if self.round_count > 0 and self.won_last_round:
                bid = true_val * 0.80
            else:
                bid = true_val

        elif self.strategy == "spiteful":
            bid = true_val * 1.50

        elif self.strategy == "timid":
            bid = true_val * 0.50

        elif self.strategy == "epsilon_greedy":
            if random.random() < 0.10:
                bid = random.uniform(0, 200)
            else:
                bid = true_val

        elif self.strategy == "trend_follower":
            if len(self.history_winning_bids) >= 2:
                trend = self.history_winning_bids[-1] - self.history_winning_bids[-2]
                bid = max(0.0, true_val + trend)
            else:
                bid = true_val

        elif self.strategy == "memory_3_avg":
            if len(self.history_my_bids) >= 3:
                bid = sum(self.history_my_bids[-3:]) / 3.0
            else:
                bid = true_val

        elif self.strategy == "competitor_aware":
            if self.round_count > 0 and not self.won_last_round:
                bid = true_val + 5.0
            else:
                bid = true_val

        elif self.strategy == "win_stay_lose_shift":
            if self.round_count > 0:
                if self.won_last_round:
                    bid = true_val
                else:
                    bid = random.uniform(0, 200)
            else:
                bid = true_val

        elif self.strategy == "strategy_switcher":
            if self.round_count >= 10:
                win_rate = self.win_count / self.round_count
                if win_rate < 0.10:
                    bid = true_val * 1.20 
                else:
                    bid = true_val
            else:
                bid = true_val

        self.history_my_bids.append(bid)
        return max(0.0, float(bid))

    async def setup(self):
        """
        Configures the communication client properties and starts the listening behavior.
        """
        self.client.host = XMPP_HOST
        self.client.port = XMPP_PORT
        self.client.force_starttls = False
        self.client.use_ssl = False
        self.add_behaviour(self.BidBehaviour())

    class BidBehaviour(CyclicBehaviour):
        async def run(self):
            """
            Listens for requests from the auctioneer, generates bids, and processes round results.
            """
            msg = await self.receive(timeout=5)
            if not msg:
                await asyncio.sleep(0.05)
                return

            content = json.loads(msg.body)

            if content["performative"] == "cfp":
                true_val = random.uniform(50.0, 150.0)
                my_bid = self.agent.calculate_bid(true_val)
                
                reply = Message(to=str(msg.sender))
                reply.body = json.dumps({
                    "performative": "propose",
                    "player_id": self.agent.player_id,
                    "bid": my_bid,
                    "true_val": true_val
                })
                await self.send(reply)

            elif content["performative"] == "inform":
                self.agent.round_count += 1
                winner_id = content["winner_id"]
                winning_bid = content["winning_bid"]
                
                self.agent.history_winning_bids.append(winning_bid)
                
                if winner_id == self.agent.player_id:
                    self.agent.won_last_round = True
                    self.agent.win_count += 1
                else:
                    self.agent.won_last_round = False


# ================= AUCTIONEER AGENT =================
class AuctioneerAgent(Agent):
    """
    Manages the auction process, evaluates bids, applies Vickrey rules, and logs outcomes.
    """
    def __init__(self, jid, password, player_jids, player_strategies):
        """
        Initializes the environment manager.
        
        Args:
            jid (str): The Jabber ID for XMPP communication.
            password (str): The password for the XMPP server.
            player_jids (list[str]): Connection addresses for active bidders.
            player_strategies (dict): Mapping of player identifiers to assigned strategies.
        """
        super().__init__(jid, password)
        self.player_jids = player_jids
        self.player_strategies = player_strategies
        self.current_round = 1
        self.history = []
        self.finished = False

        self.total_profits = {i: 0.0 for i in range(1, len(player_jids) + 1)}

    async def setup(self):
        """
        Configures the communication client properties and initiates the master game loop.
        """
        self.client.host = XMPP_HOST
        self.client.port = XMPP_PORT
        self.client.force_starttls = False
        self.client.use_ssl = False

        await asyncio.sleep(2)
        self.add_behaviour(self.AuctionManagerBehaviour())

    class AuctionManagerBehaviour(CyclicBehaviour):
        async def run(self):
            """
            Executes the core round sequence: calls for proposals, processes responses, determines pricing, and logs data.
            """
            if self.agent.current_round > ROUNDS:
                logger.info("Simulation finished.")
                self.agent.finished = True
                self.kill()
                return

            # Request Bids
            for p_jid in self.agent.player_jids:
                msg = Message(to=p_jid)
                msg.body = json.dumps({"performative": "cfp"})
                await self.send(msg)

            bids_received = {}
            true_vals = {}
            start = asyncio.get_event_loop().time()

            # Collect Bids
            while len(bids_received) < len(self.agent.player_jids):
                if asyncio.get_event_loop().time() - start > 10:
                    logger.warning("Round timeout - missing bids.")
                    break

                msg = await self.receive(timeout=2)
                if msg:
                    content = json.loads(msg.body)
                    if content["performative"] == "propose":
                        pid = content["player_id"]
                        bids_received[pid] = content["bid"]
                        true_vals[pid] = content["true_val"]

            if len(bids_received) == 0:
                self.agent.current_round += 1
                return

            # Determine Winner and Price
            sorted_bids = sorted(bids_received.items(), key=lambda item: item[1], reverse=True)
            winner_id = sorted_bids[0][0]
            winning_bid = sorted_bids[0][1]
            second_price = sorted_bids[1][1] if len(sorted_bids) > 1 else winning_bid

            # Calculate Profit
            round_profits = {pid: 0.0 for pid in bids_received.keys()}
            winner_true_val = true_vals[winner_id]
            profit = winner_true_val - second_price
            round_profits[winner_id] = profit
            self.agent.total_profits[winner_id] += profit

            # Log History
            row = {
                "Round": self.agent.current_round,
                "Winner_ID": winner_id,
                "Winning_Bid": winning_bid,
                "Second_Price": second_price
            }

            for pid in self.agent.player_strategies.keys():
                row[f"P{pid}_Strategy"] = self.agent.player_strategies[pid]
                row[f"P{pid}_TrueVal"] = true_vals.get(pid, 0.0)
                row[f"P{pid}_Bid"] = bids_received.get(pid, 0.0)
                row[f"P{pid}_Profit"] = round_profits.get(pid, 0.0)
                row[f"P{pid}_TotalProfit"] = self.agent.total_profits.get(pid, 0.0)

            self.agent.history.append(row)

            # Broadcast Results
            for p_jid in self.agent.player_jids:
                msg = Message(to=p_jid)
                msg.body = json.dumps({
                    "performative": "inform",
                    "winner_id": winner_id,
                    "winning_bid": winning_bid,
                    "second_price": second_price
                })
                await self.send(msg)

            self.agent.current_round += 1


# ================= MAIN EXECUTION =================
async def run_simulation():
    """
    Constructs the simulation environment, deploys the active agents, and outputs the final historical dataset.
    """
    logger.info("Starting Vickrey Auction Simulation")

    uid = uuid.uuid4().hex[:6]
    strategies = StrategySelector.get_selected_strategies()
    num_agents = len(strategies)

    player_jids = [f"bidder{i}@{XMPP_DOMAIN}/{uid}_{i}" for i in range(1, num_agents + 1)]
    players = []
    player_strategies = {}

    for i in range(num_agents):
        strategy_name = strategies[i]
        player_id = i + 1
        player_strategies[player_id] = strategy_name
        
        p = BidderAgent(
            jid=player_jids[i], 
            password=PASSWORD, 
            player_id=player_id, 
            strategy=strategy_name
        )
        await p.start(auto_register=True)
        players.append(p)

    auctioneer = AuctioneerAgent(
        jid=f"auctioneer@{XMPP_DOMAIN}/{uid}_mgr",
        password=PASSWORD,
        player_jids=player_jids,
        player_strategies=player_strategies
    )

    await auctioneer.start(auto_register=True)

    while not auctioneer.finished:
        await asyncio.sleep(0.5)

    df = pd.DataFrame(auctioneer.history)
    filename = "vickrey_auction_results.csv"
    df.to_csv(filename, index=False)
    logger.info(f"Results exported to {filename}")

    for p in players:
        await p.stop()
    await auctioneer.stop()
    await asyncio.sleep(1)

async def main():
    """
    Configures the system event loop and executes the simulation run.
    """
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    await run_simulation()
    print("Simulation complete.")

if __name__ == "__main__":
    asyncio.run(main())