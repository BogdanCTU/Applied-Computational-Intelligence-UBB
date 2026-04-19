import asyncio
import json
import random
import logging
import sys
import math
import statistics
import pandas as pd
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import platform
import uuid

# ================= LOGGING =================
logger = logging.getLogger("simulation")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler("simulation_log.txt", mode="w")
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("spade").setLevel(logging.WARNING)
logging.getLogger("slixmpp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# ================= PARAMETERS =================
M = 7
H = 100

B = 1.0
A = 2.0 * B
C = 10.0

XMPP_DOMAIN = "localhost"
XMPP_HOST = "127.0.0.1"
XMPP_PORT = 5222
PASSWORD = "admin"

class StrategySelector:
    """
    Provides a curated list of strategies for a Multiagent System simulation.
    The selected strategies represent unique behaviors suitable for the Minimum Effort Game.
    """

    @staticmethod
    def get_selected_strategies() -> list[str]:
        """
        Returns a list of exactly twenty specific strategy identifiers.
        The list includes a mix of baseline heuristics, game-theoretic models,
        and learning algorithms specifically chosen for weak-link dynamics.

        Returns:
            list[str]: A list of strategy names formatted for the simulation environment.
        """
        selected_strategies = [
            # ================= CORE HEURISTICS =================
            "always_low",      # Chooses the lowest effort. This acts as the safest choice and a stable baseline.
            "always_high",     # Chooses the highest effort. This aims for the maximum reward but carries high risk.
            "random",          # Chooses an effort without a pattern. This introduces noise into the simulation.
            "imitate_min",     # Copies the lowest effort from the previous round. This directly reacts to the weakest link rule.
            "gradual_up",      # Slowly increases effort step-by-step. This models an attempt to build group trust.
            "gradual_down",    # Slowly decreases effort step-by-step. This models a reaction to poor group coordination.
            "win_stay",        # Keeps the current effort level if the previous round resulted in a high reward.
            "lose_shift",      # Changes the effort level if the previous round resulted in a low reward.

            # ================= MEMORY & PREDICTIVE =================
            "predict_min",     # Analyzes past data to guess the lowest effort for the next round.
            "trend_following", # Moves effort in the same direction as the group's recent historical changes.
            "memory_3_step",   # Relies strictly on the outcomes of the last three rounds to determine the next action.

            # ================= GAME-THEORETIC =================
            "best_response",   # Calculates the optimal mathematical move assuming opponents repeat their last action.
            "fictitious_play", # Builds a long-term probability model of opponent actions and responds to the distribution.
            "risk_dominant",   # Chooses the effort that minimizes potential loss rather than maximizing potential gain.
            "regret_minimization", # Evaluates past rounds to select the effort that would have yielded the best historical outcome.
            "stochastic_best_response", # Calculates the best response but applies a small probability of random error.

            # ================= LEARNING & SOCIAL =================
            "bandit_ucb",      # Uses a statistical formula to balance exploring new efforts and exploiting known successful efforts.
            "q_learning_low",  # Applies a reinforcement learning algorithm to discover the best long-term policy.
            "consensus_seek",  # Identifies the most common effort in the group and attempts to match it.

            # ================= META =================
            "strategy_switcher" # Monitors internal performance and swaps to a different logic model if rewards drop below a threshold.
        ]
        
        return selected_strategies


# ================= PLAYER =================
class PlayerAgent(Agent):
    """
    Represents an independent actor in the simulation.
    Maintains internal state regarding past rounds and executes a designated decision-making strategy.
    """
    def __init__(self, jid, password, player_id, strategy):
        """
        Initializes the agent with identification details, starting parameters, and a specific behavioral strategy.
        
        Args:
            jid (str): The Jabber ID for XMPP communication.
            password (str): The password for the XMPP server.
            player_id (int): The unique numerical identifier for the player.
            strategy (str): The name of the decision-making logic the agent will use.
        """
        super().__init__(jid, password)
        self.player_id = player_id
        self.strategy = strategy
        self.current_effort = random.randint(1, M)
        
        # State tracking variables
        self.round_count = 0
        self.history_min_efforts = []
        self.history_my_efforts = []
        self.history_my_payoffs = []
        self.history_min_others = []
        
        # Variables for learning algorithms
        self.action_counts = {a: 0 for a in range(1, M + 1)}
        self.q_values = {a: 0.0 for a in range(1, M + 1)}
        self.regret_sum = {a: 0.0 for a in range(1, M + 1)}

    def calculate_hypothetical_payoff(self, action: int, min_of_others: int) -> float:
        """
        Calculates the theoretical reward an action would have produced given the minimum effort of all other participants.
        
        Args:
            action (int): The hypothetical effort level chosen.
            min_of_others (int): The lowest effort chosen by all other participants.
            
        Returns:
            float: The calculated reward outcome based on the game mathematical formula.
        """
        effective_min = min(action, min_of_others)
        return (A * effective_min) - (B * action) + C

    def apply_strategy(self, min_effort: int, payoffs: dict, efforts: dict):
        """
        Updates internal tracking variables based on round results.
        Executes the assigned behavioral strategy to determine the effort level for the upcoming round.
        
        Args:
            min_effort (int): The lowest effort level submitted by the entire group in the previous round.
            payoffs (dict): A mapping of player identifiers to their calculated rewards for the previous round.
            efforts (dict): A mapping of player identifiers to their submitted effort levels for the previous round.
        """
        self.round_count += 1
        self.history_min_efforts.append(min_effort)
        
        my_payoff = payoffs.get(str(self.player_id), 0)
        self.history_my_payoffs.append(my_payoff)
        
        my_last_effort = efforts.get(str(self.player_id), self.current_effort)
        self.history_my_efforts.append(my_last_effort)

        others_efforts = [eff for pid, eff in efforts.items() if str(pid) != str(self.player_id)]
        min_of_others = min(others_efforts) if others_efforts else min_effort
        self.history_min_others.append(min_of_others)

        # Update learning models
        self.action_counts[my_last_effort] += 1
        
        # Regret update
        for a in range(1, M + 1):
            hypothetical = self.calculate_hypothetical_payoff(a, min_of_others)
            self.regret_sum[a] += (hypothetical - my_payoff)
            
        # Q-learning update (Alpha = 0.1)
        alpha = 0.1
        self.q_values[my_last_effort] = ((1.0 - alpha) * self.q_values[my_last_effort]) + (alpha * my_payoff)

        # Apply specific strategy logic
        next_effort = self.current_effort

        if self.strategy == "always_low":
            next_effort = 1

        elif self.strategy == "always_high":
            next_effort = M

        elif self.strategy == "random":
            next_effort = random.randint(1, M)

        elif self.strategy == "imitate_min":
            next_effort = min_effort

        elif self.strategy == "gradual_up":
            next_effort = min(M, self.current_effort + 1)

        elif self.strategy == "gradual_down":
            next_effort = max(1, self.current_effort - 1)

        elif self.strategy == "win_stay":
            ideal_payoff = self.calculate_hypothetical_payoff(my_last_effort, my_last_effort)
            if my_payoff >= ideal_payoff:
                next_effort = self.current_effort
            else:
                next_effort = random.randint(1, M)

        elif self.strategy == "lose_shift":
            ideal_payoff = self.calculate_hypothetical_payoff(my_last_effort, my_last_effort)
            if my_payoff < ideal_payoff:
                next_effort = random.randint(1, M)
            else:
                next_effort = self.current_effort

        elif self.strategy == "predict_min":
            recent_mins = self.history_min_efforts[-3:]
            next_effort = round(sum(recent_mins) / len(recent_mins)) if recent_mins else 1

        elif self.strategy == "trend_following":
            if len(self.history_min_efforts) >= 2:
                diff = self.history_min_efforts[-1] - self.history_min_efforts[-2]
                next_effort = max(1, min(M, self.current_effort + diff))
            else:
                next_effort = self.current_effort

        elif self.strategy == "memory_3_step":
            if len(self.history_min_efforts) >= 3:
                next_effort = self.history_min_efforts[-3]
            else:
                next_effort = random.randint(1, M)

        elif self.strategy == "best_response":
            next_effort = min_of_others

        elif self.strategy == "fictitious_play":
            if self.history_min_others:
                most_frequent = max(set(self.history_min_others), key=self.history_min_others.count)
                next_effort = most_frequent
            else:
                next_effort = 1

        elif self.strategy == "risk_dominant":
            next_effort = 1

        elif self.strategy == "regret_minimization":
            positive_regrets = {a: max(0.0, r) for a, r in self.regret_sum.items()}
            total_regret = sum(positive_regrets.values())
            if total_regret > 0:
                rand_val = random.uniform(0, total_regret)
                cumulative = 0.0
                for a, r in positive_regrets.items():
                    cumulative += r
                    if rand_val <= cumulative:
                        next_effort = a
                        break
            else:
                next_effort = random.randint(1, M)

        elif self.strategy == "stochastic_best_response":
            if random.random() < 0.90:
                next_effort = min_of_others
            else:
                next_effort = random.randint(1, M)

        elif self.strategy == "bandit_ucb":
            ucb_values = {}
            for a in range(1, M + 1):
                if self.action_counts[a] == 0:
                    ucb_values[a] = float('inf')
                else:
                    exploitation = self.q_values[a]
                    exploration = math.sqrt((2 * math.log(self.round_count)) / self.action_counts[a])
                    ucb_values[a] = exploitation + exploration
            next_effort = max(ucb_values, key=ucb_values.get)

        elif self.strategy == "q_learning_low":
            if random.random() < 0.10:
                next_effort = random.randint(1, M)
            else:
                next_effort = max(self.q_values, key=self.q_values.get)

        elif self.strategy == "consensus_seek":
            all_efforts = list(efforts.values())
            if all_efforts:
                next_effort = statistics.mode(all_efforts)
            else:
                next_effort = self.current_effort

        elif self.strategy == "strategy_switcher":
            if len(self.history_my_payoffs) >= 5:
                recent_avg = sum(self.history_my_payoffs[-5:]) / 5.0
                if recent_avg < 12.0:
                    next_effort = 1
                else:
                    next_effort = min_of_others
            else:
                next_effort = min_of_others

        # Boundary enforcement
        self.current_effort = max(1, min(M, int(next_effort)))

    async def setup(self):
        """
        Configures the communication client properties and adds the core cyclical communication behavior.
        """
        self.client.host = XMPP_HOST
        self.client.port = XMPP_PORT
        self.client.force_starttls = False
        self.client.use_ssl = False

        self.add_behaviour(self.PlayBehaviour())

    class PlayBehaviour(CyclicBehaviour):
        async def run(self):
            """
            Executes the continuous loop for receiving messages, replying with current effort, and processing round results.
            """
            msg = await self.receive(timeout=5)

            if not msg:
                await asyncio.sleep(0.05)
                return

            content = json.loads(msg.body)

            if content["performative"] == "request_effort":
                reply = Message(to=str(msg.sender))
                reply.body = json.dumps({
                    "player_id": self.agent.player_id,
                    "effort": self.agent.current_effort
                })
                await self.send(reply)

            elif content["performative"] == "round_result":
                self.agent.apply_strategy(
                    min_effort=content["min_effort"],
                    payoffs=content["payoffs"],
                    efforts=content["efforts"]
                )


# ================= CONTROLLER =================
class ControllerAgent(Agent):
    def __init__(self, jid, password, player_jids, num_agents, player_strategies):
        """
        Initializes the simulation manager with player connections, tracking variables, and strategy records.
        
        Args:
            jid (str): The Jabber ID for XMPP communication.
            password (str): The password for the XMPP server.
            player_jids (list[str]): A list of connection addresses for all active player agents.
            num_agents (int): The total count of active player agents.
            player_strategies (dict): A mapping of player identifiers to their assigned strategy names.
        """
        super().__init__(jid, password)
        self.player_jids = player_jids
        self.num_agents = num_agents
        self.player_strategies = player_strategies

        self.current_round = 1
        self.history = []
        self.finished = False

        # GLOBAL SCORE TRACKING
        self.scores = {i: 0 for i in range(1, num_agents + 1)}

    async def setup(self):
        """
        Configures the communication client properties and adds the main game loop control behavior.
        """
        self.client.host = XMPP_HOST
        self.client.port = XMPP_PORT
        self.client.force_starttls = False
        self.client.use_ssl = False

        await asyncio.sleep(2)
        self.add_behaviour(self.GameManagerBehaviour())

    class GameManagerBehaviour(CyclicBehaviour):
        async def run(self):
            """
            Executes the main simulation loop, requesting efforts, calculating payoffs, and recording data to history.
            """
            if self.agent.current_round > H:
                logger.info(f"Simulation finished (N={self.agent.num_agents})")
                self.agent.finished = True
                self.kill()
                return

            logger.info(f"N={self.agent.num_agents} | Round {self.agent.current_round}")

            # ================= REQUEST =================
            for p_jid in self.agent.player_jids:
                msg = Message(to=p_jid)
                msg.body = json.dumps({"performative": "request_effort"})
                await self.send(msg)

            efforts = {}
            start = asyncio.get_event_loop().time()

            # ================= COLLECT =================
            while len(efforts) < len(self.agent.player_jids):
                if asyncio.get_event_loop().time() - start > 10:
                    logger.warning("Round timeout")
                    break

                msg = await self.receive(timeout=2)
                if msg:
                    content = json.loads(msg.body)
                    efforts[content["player_id"]] = content["effort"]

            if len(efforts) != len(self.agent.player_jids):
                self.agent.current_round += 1
                return

            # ================= PAYOFF =================
            min_effort = min(efforts.values())

            payoffs = {
                pid: A * min_effort - B * eff + C
                for pid, eff in efforts.items()
            }

            # ================= UPDATE SCORES =================
            for pid, payoff in payoffs.items():
                pid_int = int(pid)
                self.agent.scores[pid_int] += payoff

            # ================= HISTORY ROW =================
            row = {
                "Round": self.agent.current_round,
                "Min_Effort": min_effort,
                "Num_Agents": self.agent.num_agents
            }

            for pid in range(1, self.agent.num_agents + 1):
                row[f"P{pid}_Strategy"] = self.agent.player_strategies[pid]
                row[f"P{pid}_Effort"] = efforts.get(pid, 0)
                row[f"P{pid}_Payoff"] = payoffs.get(pid, 0)

            self.agent.history.append(row)

            # ================= BROADCAST =================
            for p_jid in self.agent.player_jids:
                msg = Message(to=p_jid)
                msg.body = json.dumps({
                    "performative": "round_result",
                    "min_effort": min_effort,
                    "payoffs": payoffs,
                    "efforts": efforts
                })
                await self.send(msg)

            self.agent.current_round += 1


# ================= SIMULATION =================
async def run_simulation(num_agents):
    """
    Instantiates the agents, distributes unique strategies, manages the simulation runtime, and exports the final data.
    
    Args:
        num_agents (int): The total number of agents to instantiate for the current simulation run.
    """
    logger.info(f"Starting simulation N={num_agents}")

    uid = uuid.uuid4().hex[:6]

    player_jids = [
        f"player{i}@{XMPP_DOMAIN}/{uid}_{i}"
        for i in range(1, num_agents + 1)
    ]

    players = []
    player_strategies = {}
    
    # Retrieve strategies and ensure assignment is unique
    available_strategies = StrategySelector.get_selected_strategies()
    random.shuffle(available_strategies)
    assigned_strategies = available_strategies[:num_agents]

    for i in range(num_agents):
        strategy_name = assigned_strategies[i]
        player_id = i + 1
        player_strategies[player_id] = strategy_name
        
        p = PlayerAgent(
            jid=player_jids[i], 
            password=PASSWORD, 
            player_id=player_id, 
            strategy=strategy_name
        )
        await p.start(auto_register=True)
        players.append(p)

    controller = ControllerAgent(
        jid=f"manager@{XMPP_DOMAIN}/{uid}_mgr",
        password=PASSWORD,
        player_jids=player_jids,
        num_agents=num_agents,
        player_strategies=player_strategies
    )

    await controller.start(auto_register=True)

    while not controller.finished:
        await asyncio.sleep(0.2)

    # ================= FINAL SCORE ROW =================
    final_row = {
        "Round": "TOTAL",
        "Min_Effort": "",
        "Num_Agents": num_agents
    }

    for pid in range(1, num_agents + 1):
        final_row[f"P{pid}_Strategy"] = player_strategies[pid]
        final_row[f"P{pid}_Effort"] = ""
        final_row[f"P{pid}_Payoff"] = controller.scores[pid]

    controller.history.append(final_row)

    # ================= WINNER LOG =================
    winner = max(controller.scores, key=controller.scores.get)

    logger.info(f"Winner for N={num_agents}: Player {winner} "
                f"with score {controller.scores[winner]}")

    # ================= SAVE CSV =================
    df = pd.DataFrame(controller.history)
    filename = f"results_N{num_agents}.csv"
    df.to_csv(filename, index=False)

    logger.info(f"Saved {filename}")

    # ================= CLEANUP =================
    for p in players:
        await p.stop()

    await controller.stop()

    await asyncio.sleep(1)


# ================= MAIN =================
async def main():
    """
    Configures the asynchronous execution environment and sequentially triggers simulations across varying group sizes.
    """
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    #for n in range(2, 10):
    #    print(f"Running N={n}")
    #    await run_simulation(n)
    #    await asyncio.sleep(2)

        print(f"Running N={20}")
        await run_simulation(20)
        await asyncio.sleep(2)

    print("All simulations completed.")


if __name__ == "__main__":
    asyncio.run(main())