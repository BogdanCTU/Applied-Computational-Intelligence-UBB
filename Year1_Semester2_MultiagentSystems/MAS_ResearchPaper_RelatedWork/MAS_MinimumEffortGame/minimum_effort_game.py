import asyncio
import json
import random
import csv
import logging
import uuid
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import platform

# Set up logging to a file instead of the terminal
logging.basicConfig(
    filename='simulation_log.txt',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

# ==========================================
# GLOBAL VARIABLES: GAME PARAMETERS
# ==========================================
N = 25  # Number of agents (players)
M = 10  # Number of strategies (effort levels: 1 to M)
H = 100 # Number of rounds

# Payoff function parameters: Pi(s) = A * min(ej) - B * ei + C
A = 2.0
B = 1.0
C = 10.0

XMPP_SERVER = 'localhost'   # localhost or der00032ldns
PASSWORD = 'admin'


class PlayerAgent(Agent):
    def __init__(self, jid, password, player_id):
        super().__init__(jid, password)
        self.player_id = player_id
        # Strategy selection: initially select a random effort between 1 and M
        self.current_effort = random.randint(1, M)
        
        # Randomly assign one of the 25 strategies
        self.strategy = random.choice([
            "random",
            "always_high",
            "always_low",
            "midpoint",
            "tit_for_tat",
            "best_response",
            "imitate_min",
            "imitate_max",
            "imitate_mean",
            "win_stay",
            "lose_shift",
            "gradual_increase",
            "gradual_decrease",
            "epsilon_greedy_low",
            "epsilon_greedy_high",
            "threshold_low",
            "threshold_high",
            "anti_coordination",
            "bounded_rational_low",
            "bounded_rational_high",
            "probabilistic_bias_low",
            "probabilistic_bias_high",
            "copy_random_agent",
            "sticky_last_action",
            "noise_perturbation"
        ])

    class PlayBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                content = json.loads(msg.body)
                
                # If controller requests effort for the current round
                if content['performative'] == 'request_effort':
                    reply = Message(to=str(msg.sender))
                    reply.set_metadata("performative", "inform_effort")
                    reply.body = json.dumps({
                        "player_id": self.agent.player_id, 
                        "effort": self.agent.current_effort
                    })
                    await self.send(reply)
                
                # If controller sends the results of the round
                elif content['performative'] == 'round_result':
                    min_effort = content['min_effort']
                    payoff = content['payoffs'][str(self.agent.player_id)]
                    prev = self.agent.current_effort
                    
                    s = self.agent.strategy

                    if s == "random":
                        self.agent.current_effort = random.randint(1, M)

                    elif s == "always_high":
                        self.agent.current_effort = M

                    elif s == "always_low":
                        self.agent.current_effort = 1

                    elif s == "midpoint":
                        self.agent.current_effort = M // 2

                    elif s == "tit_for_tat":
                        self.agent.current_effort = min_effort

                    elif s == "best_response":
                        self.agent.current_effort = min_effort

                    elif s == "imitate_min":
                        self.agent.current_effort = min_effort

                    elif s == "imitate_max":
                        self.agent.current_effort = max(content.get("efforts", {str(self.agent.player_id): prev}).values())

                    elif s == "imitate_mean":
                        # Convert all effort keys to string for consistent lookup since JSON keys are strings
                        effs = content.get("efforts", {})
                        if effs:
                            self.agent.current_effort = int(sum(effs.values()) / len(effs))
                        else:
                            self.agent.current_effort = prev

                    elif s == "win_stay":
                        self.agent.current_effort = prev if payoff >= 0 else random.randint(1, M)

                    elif s == "lose_shift":
                        # If payoff is less than if they had played high (theoretical maximum at min_effort) - loosely following user snippet
                        self.agent.current_effort = prev + 1 if payoff < (A * min_effort - B * prev + C) else prev
                        self.agent.current_effort = max(1, min(M, self.agent.current_effort))

                    elif s == "gradual_increase":
                        self.agent.current_effort = min(M, prev + 1)

                    elif s == "gradual_decrease":
                        self.agent.current_effort = max(1, prev - 1)

                    elif s == "epsilon_greedy_low":
                        self.agent.current_effort = min_effort if random.random() < 0.8 else random.randint(1, M)

                    elif s == "epsilon_greedy_high":
                        self.agent.current_effort = M if random.random() < 0.8 else random.randint(1, M)

                    elif s == "threshold_low":
                        self.agent.current_effort = 1 if min_effort <= M/2 else min_effort

                    elif s == "threshold_high":
                        self.agent.current_effort = M if min_effort >= M/2 else min_effort

                    elif s == "anti_coordination":
                        self.agent.current_effort = max(1, min(M, M - min_effort + 1))

                    elif s == "bounded_rational_low":
                        self.agent.current_effort = max(1, min_effort - 1)

                    elif s == "bounded_rational_high":
                        self.agent.current_effort = min(M, min_effort + 1)

                    elif s == "probabilistic_bias_low":
                        self.agent.current_effort = random.choices(range(1, M+1), weights=[M-i for i in range(M)])[0]

                    elif s == "probabilistic_bias_high":
                        self.agent.current_effort = random.choices(range(1, M+1), weights=[i+1 for i in range(M)])[0]

                    elif s == "copy_random_agent":
                        self.agent.current_effort = random.choice(list(content.get("efforts", {str(self.agent.player_id): prev}).values()))

                    elif s == "sticky_last_action":
                        self.agent.current_effort = prev

                    elif s == "noise_perturbation":
                        self.agent.current_effort = max(1, min(M, prev + random.choice([-1, 0, 1])))
            else:
                pass

    async def setup(self):
        b = self.PlayBehaviour()
        self.add_behaviour(b)


class ControllerAgent(Agent):
    def __init__(self, jid, password, player_jids):
        super().__init__(jid, password)
        self.player_jids = player_jids
        self.current_round = 1
        self.history = []  # Store round data for CSV export

    class GameManagerBehaviour(CyclicBehaviour):
        async def run(self):
            if self.agent.current_round > H:
                logging.debug("\n[CONTROLLER] Simulation finished. Exporting to CSV...")
                
                # Export to CSV
                try:
                    with open('minimum_effort_game_results.csv', 'w', newline='') as f:
                        writer = csv.writer(f)
                        # Create header
                        header = ['Round', 'Min_Effort']
                        for i in range(1, len(self.agent.player_jids) + 1):
                            header.extend([f'P{i}_Effort', f'P{i}_Payoff'])
                        writer.writerow(header)
                        
                        # Write data
                        for row in self.agent.history:
                            writer.writerow(row)
                    logging.debug("[CONTROLLER] CSV exported to minimum_effort_game_results.csv")
                except Exception as e:
                    logging.error(f"[CONTROLLER] Failed to export CSV: {e}")
                
                self.kill()
                return

            logging.debug(f"\n{'='*40}")
            logging.debug(f"--- ROUND {self.agent.current_round} ---")
            logging.debug(f"{'='*40}")
            
            # 1. Request effort from all players
            for p_jid in self.agent.player_jids:
                msg = Message(to=p_jid)
                msg.set_metadata("performative", "request")
                msg.body = json.dumps({"performative": "request_effort"})
                await self.send(msg)
            
            # 2. Wait for responses from all players
            efforts = {}
            for _ in range(len(self.agent.player_jids)):
                msg = None
                while not msg:
                    msg = await self.receive(timeout=10)
                content = json.loads(msg.body)
                if "effort" in content:
                    efforts[content["player_id"]] = content["effort"]

            # 3. Calculate game logic
            if efforts:
                # Find minimum effort
                min_effort = min(efforts.values())
                
                # Calculate payoffs
                payoffs = {}
                for pid, eff in efforts.items():
                    # Pi(s) = A * min(ej) - B * ei + C
                    payoffs[pid] = A * min_effort - B * eff + C

                logging.debug(f"[CONTROLLER] Player Efforts: {efforts}")
                logging.debug(f"[CONTROLLER] Minimum Effort: {min_effort}")
                logging.debug(f"[CONTROLLER] Resulting Payoffs: {payoffs}")

                # Save round data for CSV export
                # Row format: Round, Min_Effort, P1_Eff, P1_Payoff, P2_Eff, P2_Payoff...
                row = [self.agent.current_round, min_effort]
                for pid in range(1, len(self.agent.player_jids) + 1):
                    row.extend([efforts.get(pid, 0), payoffs.get(pid, 0)])
                self.agent.history.append(row)

                # 4. Send results back so players can adapt their strategy
                for p_jid in self.agent.player_jids:
                    msg = Message(to=p_jid)
                    msg.set_metadata("performative", "inform")
                    msg.body = json.dumps({
                        "performative": "round_result",
                        "min_effort": min_effort,
                        "payoffs": payoffs,
                        "efforts": efforts
                    })
                    await self.send(msg)
            
            self.agent.current_round += 1
            await asyncio.sleep(1) # Pauses briefly between rounds

    async def setup(self):
        b = self.GameManagerBehaviour()
        self.add_behaviour(b)


async def main():
    logging.info("Setting up Minimum Effort Game Simulation...")
    logging.info(f"Number of agents (N) = {N}")
    logging.info(f"Number of strategies (M) = {M} (Effort Levels: 1 to {M})")
    
    uid = str(uuid.uuid4())[:8]
    
    # 1. Initialize Player Agents
    player_jids = [f"player{i}_{uid}@{XMPP_SERVER}" for i in range(1, N+1)]
    players = []
    
    for i in range(1, N+1):
        p = PlayerAgent(player_jids[i-1], PASSWORD, i)
        await p.start(auto_register=True)
        players.append(p)
    
    # 2. Initialize Controller Agent
    controller = ControllerAgent(f"manager_{uid}@{XMPP_SERVER}", PASSWORD, player_jids)
    await controller.start(auto_register=True)
    
    # 3. Wait for the simulation to finish
    while controller.is_alive():
        try:
            await asyncio.sleep(1)
        except KeyboardInterrupt:
            logging.warning("Simulation externally interrupted.")
            break

    # 4. Cleanup
    for p in players:
        await p.stop()
    await controller.stop()
    logging.info("All agents stopped. Exiting.")


if __name__ == "__main__":
    # Required for Windows platform to avoid EventLoop closure issues in SPADE
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
