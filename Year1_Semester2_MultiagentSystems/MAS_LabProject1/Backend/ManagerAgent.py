import asyncio
import csv
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message

class ManagerAgent(Agent):
    """
    Manager Entity coordinating the matches, syncing execution and compiling scores.
    Outputs per-round actions, payoffs, and cumulative points for both players.
    """

    class MatchRunner(OneShotBehaviour):
        def __init__(self, rounds, T, R, P, S, player1_jid, player2_jid, results_list, result_callback):
            super().__init__()
            self.rounds = rounds
            self.T = T
            self.R = R
            self.P = P
            self.S = S
            self.player1_jid = player1_jid
            self.player2_jid = player2_jid
            self.results_list = results_list
            self.result_callback = result_callback

        async def run(self):

            # Initialize cumulative scores
            p1_cumulative = 0
            p2_cumulative = 0

            for round_idx in range(1, self.rounds + 1):
                # Request moves via XMPP
                req1 = Message(to=self.player1_jid)
                req1.set_metadata("performative", "request")
                req1.set_metadata("ontology", "REQUEST_ACTION")
                await self.send(req1)

                req2 = Message(to=self.player2_jid)
                req2.set_metadata("performative", "request")
                req2.set_metadata("ontology", "REQUEST_ACTION")
                await self.send(req2)

                # Collect responses
                resp1 = await self.receive(timeout=3)
                resp2 = await self.receive(timeout=3)

                if resp1 and resp2:
                    action1 = resp1.body
                    action2 = resp2.body
                    payoff1, payoff2 = self.evaluate(action1, action2)

                    # Update cumulative scores
                    p1_cumulative += payoff1
                    p2_cumulative += payoff2

                    # Store result as a dictionary
                    result_entry = {
                        "Round": round_idx,
                        "Player1_Action": action1,
                        "Player1_Payoff": payoff1,
                        "Player1_ActualPoints": p1_cumulative,
                        "Player2_Action": action2,
                        "Player2_Payoff": payoff2,
                        "Player2_ActualPoints": p2_cumulative
                    }
                    self.results_list.append(result_entry)
                    if self.result_callback:
                        self.result_callback(result_entry)

                    # Send results back to players
                    res_msg1 = Message(to=self.player1_jid)
                    res_msg1.set_metadata("performative", "inform")
                    res_msg1.set_metadata("ontology", "ROUND_RESULT")
                    res_msg1.body = f"{action2},{payoff1},{payoff2}"
                    await self.send(res_msg1)

                    res_msg2 = Message(to=self.player2_jid)
                    res_msg2.set_metadata("performative", "inform")
                    res_msg2.set_metadata("ontology", "ROUND_RESULT")
                    res_msg2.body = f"{action1},{payoff2},{payoff1}"
                    await self.send(res_msg2)

                else:
                    print(f"[Manager] Error: Timed out waiting for action responses on round {round_idx}")

                # Slight execution throttle
                await asyncio.sleep(0.01)

            # Match finished
            print("=== MATCH FINISHED ===")
            print(f"Total Rounds: {self.rounds}")
            print(f"Player 1 ({self.player1_jid}) Total Score: {p1_cumulative}")
            print(f"Player 2 ({self.player2_jid}) Total Score: {p2_cumulative}")

        def evaluate(self, action1, action2):
            """Evaluates choices based on T > R > P > S"""
            if action1 == "C" and action2 == "C":
                return (self.R, self.R)
            elif action1 == "D" and action2 == "D":
                return (self.P, self.P)
            elif action1 == "C" and action2 == "D":
                return (self.S, self.T)
            elif action1 == "D" and action2 == "C":
                return (self.T, self.S)
            return (0, 0)

    def __init__(self, jid, password):
        super().__init__(jid, password)
        self.match_behaviour = None

    async def setup(self):
        # Setup is empty; match will be added dynamically
        pass

    def start_match(self, rounds, T, R, P, S, p1_jid, p2_jid, results_list, result_callback):
        self.match_behaviour = self.MatchRunner(rounds, T, R, P, S, p1_jid, p2_jid, results_list, result_callback)
        self.add_behaviour(self.match_behaviour)