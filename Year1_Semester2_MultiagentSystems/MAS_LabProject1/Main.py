import asyncio
import argparse
import spade
import ManagerAgent
import PlayerAgent

from ManagerAgent import ManagerAgent
from PlayerAgent import PlayerAgent
from AgentStrategy import RandomStrategy, TitForTat, AlwaysCooperate, AlwaysDefect


async def run_simulation():
    # Hardcoded simulation parameters
    rounds = 1000   # Total iterations
    T = 5           # Temptation
    R = 3           # Reward
    P = 1           # Punishment
    S = 0           # Sucker

    # Validation step based on problem spec (T > R > P > S)
    assert T > R and R > P and P > S, "Payoff parameters must satisfy T > R > P > S."

    # XMPP Setup
    xmpp_server = "bogdanpc"
    password = "admin"

    p1_jid = f"player1@{xmpp_server}"
    p2_jid = f"player2@{xmpp_server}"
    gm_jid = f"manager@{xmpp_server}"

    print(f"Initializing simulation with {rounds} iterations...")
    print(f"Payoff Matrix: T={T}, R={R}, P={P}, S={S}")

    # Injecting strategies
    player1 = PlayerAgent(p1_jid, password, strategy=TitForTat())
    player2 = PlayerAgent(p2_jid, password, strategy=RandomStrategy())
    manager = ManagerAgent(gm_jid, password)

    try:
        # Connect agents
        await player1.start(auto_register=True)
        await player2.start(auto_register=True)
        await manager.start(auto_register=True)
        print("Actors successfully connected to XMPP.")
    except Exception as e:
        print(f"Agent Start Failed Due to Config or Router exception: {e}")
        return

    # Buffer before triggering simulation
    await asyncio.sleep(2)

    csv_file = "simulation_results.csv"
    manager.start_match(rounds, T, R, P, S, p1_jid, p2_jid, csv_file)

    if manager.match_behaviour:
        # Await simulation end
        await manager.match_behaviour.join()

    # Clean shutdown
    await player1.stop()
    await player2.stop()
    await manager.stop()
    print("Execution successfully closed.")


# Run simulation
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent System for Iterated Prisoner's Dilemma.")
    parser.add_argument("--rounds", type=int, default=1000, help="Total number of game iterations.")
    parser.add_argument("-T", type=int, default=5, help="Temptation payoff factor.")
    parser.add_argument("-R", type=int, default=3, help="Reward payoff factor.")
    parser.add_argument("-P", type=int, default=1, help="Punishment payoff factor.")
    parser.add_argument("-S", type=int, default=0, help="Sucker payoff factor.")
    
    opts = parser.parse_args()
    
    # SPADE starts in Async IO Thread Loop
    #spade.run(run_simulation(opts))

    spade.run(run_simulation())