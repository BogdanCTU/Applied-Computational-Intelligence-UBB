import asyncio
import json
import random
import logging
import statistics
import sys
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
XMPP_DOMAIN = "localhost"
XMPP_HOST = "127.0.0.1"
XMPP_PORT = 5222
PASSWORD = "admin"

# Maps round numbers (1-26) to the array of player true values (v1 to v5)
GAME_DATA = {
    1: [135, 950, 275, 500, 675],   # A
    2: [825, 785, 100, 295, 455],   # B
    3: [505, 655, 245, 805, 255],   # C
    4: [445, 835, 655, 645, 115],   # D
    5: [455, 995, 655, 105, 255],   # E
    6: [1000, 800, 500, 400, 200],  # F
    7: [200, 400, 600, 700, 950],   # G
    8: [275, 455, 990, 655, 245],   # H
    9: [105, 255, 455, 1000, 655],  # I
    10: [800, 650, 1000, 250, 450], # J
    11: [235, 435, 635, 735, 935],  # K
    12: [795, 100, 256, 545, 995],  # L
    13: [245, 795, 1000, 255, 500], # M
    14: [900, 800, 600, 400, 200],  # N
    15: [575, 785, 995, 250, 450],  # O
    16: [100, 250, 450, 750, 963],  # P
    17: [250, 150, 550, 950, 650],  # Q
    18: [880, 420, 575, 715, 185],  # R
    19: [935, 215, 550, 750, 325],  # S
    20: [175, 875, 530, 720, 445],  # T
    21: [255, 650, 805, 795, 100],  # U
    22: [995, 655, 455, 255, 245],  # V
    23: [795, 805, 105, 645, 445],  # W
    24: [245, 255, 945, 795, 500],  # X
    25: [645, 825, 100, 800, 445],  # Y
    26: [500, 800, 400, 1000, 250]  # Z
}

ROUNDS = len(GAME_DATA)

class StrategySelector:
    """
    Provides a curated list of strategies for the Vickrey Auction simulation.
    """

    @staticmethod
    def get_selected_strategies() -> list[str]:
        """
        Returns a list of exactly five specific strategy identifiers.
        
        Returns:
            list[str]: A list of strategy names formatted for the simulation environment.
        """
        return [
            "truthful",                     # Bids exact true valuation (Dominant strategy).
            "random_reasonable",            # Random bid within a realistic range around the true value.
            "underbid_bayesian",            # Bids under of true valuation (avoid winner’s curse / overpayment risk perception).
            "overbid",                      # Bids 115% of true valuation (utility-weighted preference for winning over surplus).
            "noisy_bounded_rationality",    # Cognitive noise + miscalibration.
            #"adaptive_learning"             # Adaptive best-response learner.
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

        elif self.strategy == "random_reasonable":
            lower = max(0.0, true_val * 0.85)
            upper = true_val * 1.15
            bid = random.uniform(lower, upper)

        elif self.strategy == "underbid_bayesian":
            bid = true_val * random.uniform(0.85, 1)

        elif self.strategy == "overbid":
            bid = true_val * random.uniform(1.00, 1.15)

        elif self.strategy == "noisy_bounded_rationality":
            noise = random.gauss(0, true_val * 0.10)
            bid = true_val + noise
            bid = max(0.0, bid)

        elif self.strategy == "adaptive_learning":
            if self.history_winning_bids:
                expected_threshold = statistics.mean(self.history_winning_bids)
                bid = expected_threshold * random.uniform(0.95, 1.05)
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
            Listens for requests from the auctioneer, generates bids based on provided true values, 
            and processes round results.
            """
            msg = await self.receive(timeout=5)
            if not msg:
                await asyncio.sleep(0.05)
                return

            content = json.loads(msg.body)

            if content["performative"] == "cfp":
                true_val = content["true_val"]
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
    Manages the auction process, distributes table values, evaluates bids, 
    applies Vickrey rules, and logs outcomes.
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
            Executes the core round sequence: distributes values from the lookup table, 
            calls for proposals, processes responses, determines pricing, and logs data.
            """
            if self.agent.current_round > ROUNDS:
                logger.info("Simulation finished.")
                self.agent.finished = True
                self.kill()
                return

            current_values = GAME_DATA[self.agent.current_round]

            for index, p_jid in enumerate(self.agent.player_jids):
                msg = Message(to=p_jid)
                msg.body = json.dumps({
                    "performative": "cfp",
                    "true_val": current_values[index]
                })
                await self.send(msg)

            bids_received = {}
            true_vals = {}
            start = asyncio.get_event_loop().time()

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

            sorted_bids = sorted(bids_received.items(), key=lambda item: item[1], reverse=True)
            winner_id = sorted_bids[0][0]
            winning_bid = sorted_bids[0][1]
            second_price = sorted_bids[1][1] if len(sorted_bids) > 1 else winning_bid

            round_profits = {pid: 0.0 for pid in bids_received.keys()}
            winner_true_val = true_vals[winner_id]
            profit = winner_true_val - second_price
            round_profits[winner_id] = profit
            self.agent.total_profits[winner_id] += profit

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