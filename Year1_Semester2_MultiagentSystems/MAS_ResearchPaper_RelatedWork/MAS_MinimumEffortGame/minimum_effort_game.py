import asyncio
import json
import random
import logging
import sys
import pandas as pd
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import platform
import uuid

# ================= LOGGING =================
logger = logging.getLogger("simulation")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# File handler
file_handler = logging.FileHandler("simulation_log.txt", mode="w")
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# ❗ Disable noisy libraries
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

# ================= PLAYER =================
class PlayerAgent(Agent):
    def __init__(self, jid, password, player_id):
        super().__init__(jid, password)
        self.player_id = player_id
        self.current_effort = random.randint(1, M)

    async def setup(self):
        self.client.host = XMPP_HOST
        self.client.port = XMPP_PORT
        self.client.force_starttls = False
        self.client.use_ssl = False

        self.add_behaviour(self.PlayBehaviour())

    class PlayBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)

            if not msg:
                await asyncio.sleep(0.05)
                return

            content = json.loads(msg.body)

            if content['performative'] == 'request_effort':
                reply = Message(to=str(msg.sender))
                reply.body = json.dumps({
                    "player_id": self.agent.player_id,
                    "effort": self.agent.current_effort
                })
                await self.send(reply)

            elif content['performative'] == 'round_result':
                min_effort = content['min_effort']
                prev = self.agent.current_effort

                self.agent.current_effort = max(
                    1, min(M, min_effort + random.choice([-1, 0, 1]))
                )

# ================= CONTROLLER =================
class ControllerAgent(Agent):
    def __init__(self, jid, password, player_jids, num_agents):
        super().__init__(jid, password)
        self.player_jids = player_jids
        self.num_agents = num_agents
        self.current_round = 1
        self.history = []
        self.finished = False

    async def setup(self):
        self.client.host = XMPP_HOST
        self.client.port = XMPP_PORT
        self.client.force_starttls = False
        self.client.use_ssl = False

        await asyncio.sleep(2)
        self.add_behaviour(self.GameManagerBehaviour())

    class GameManagerBehaviour(CyclicBehaviour):
        async def run(self):

            if self.agent.current_round > H:
                logger.info(f"Simulation finished (N={self.agent.num_agents})")
                self.agent.finished = True
                self.kill()
                return

            logger.info(f"N={self.agent.num_agents} | Round {self.agent.current_round}")

            # Request
            for p_jid in self.agent.player_jids:
                msg = Message(to=p_jid)
                msg.body = json.dumps({"performative": "request_effort"})
                await self.send(msg)

            efforts = {}
            start = asyncio.get_event_loop().time()

            # Collect
            while len(efforts) < len(self.agent.player_jids):
                if asyncio.get_event_loop().time() - start > 10:
                    logger.warning(f"N={self.agent.num_agents} | Round timeout")
                    break

                msg = await self.receive(timeout=2)
                if msg:
                    content = json.loads(msg.body)
                    efforts[content["player_id"]] = content["effort"]

            if len(efforts) != len(self.agent.player_jids):
                self.agent.current_round += 1
                return

            min_effort = min(efforts.values())

            payoffs = {
                str(pid): A * min_effort - B * eff + C
                for pid, eff in efforts.items()
            }

            row = {
                "Round": self.agent.current_round,
                "Min_Effort": min_effort,
                "Num_Agents": self.agent.num_agents
            }

            for pid in range(1, self.agent.num_agents + 1):
                row[f'P{pid}_Effort'] = efforts.get(pid, 0)
                row[f'P{pid}_Payoff'] = payoffs.get(str(pid), 0)

            self.agent.history.append(row)

            # Broadcast
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
    logger.info(f"Starting simulation N={num_agents}")

    uid = uuid.uuid4().hex[:6]

    player_jids = [
        f"player{i}@{XMPP_DOMAIN}/{uid}_{i}"
        for i in range(1, num_agents + 1)
    ]

    players = []

    # Start players
    for i in range(num_agents):
        p = PlayerAgent(player_jids[i], PASSWORD, i + 1)
        await p.start(auto_register=True)
        players.append(p)

    controller = ControllerAgent(
        f"manager@{XMPP_DOMAIN}/{uid}_mgr",
        PASSWORD,
        player_jids,
        num_agents
    )

    await controller.start(auto_register=True)

    # Wait until simulation finishes
    while not controller.finished:
        await asyncio.sleep(0.2)

    # Save CSV per N
    df = pd.DataFrame(controller.history)
    filename = f"results_N{num_agents}.csv"
    df.to_csv(filename, index=False)

    logger.info(f"Saved {filename}")

    # Cleanup
    for p in players:
        await p.stop()

    await controller.stop()

    await asyncio.sleep(1)

# ================= MAIN =================
async def main():
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    for n in range(2, 10):
        print(f"Running N={n}")
        await run_simulation(n)
        await asyncio.sleep(2)

    print("All simulations completed.")

if __name__ == "__main__":
    asyncio.run(main())