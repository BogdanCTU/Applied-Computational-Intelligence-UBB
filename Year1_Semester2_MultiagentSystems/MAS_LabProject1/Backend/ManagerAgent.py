import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message
from Environment import PrisonersDilemmaEnvironment

class ManagerAgent(Agent):
    """
    Manager Agent coordinating the Prisoner's Dilemma matches.
    Implements a Hybrid (Reactive + Deliberative) architecture with PAGE design:
    - Perception: receives actions from agents
    - Internal State: maintains round history and cumulative scores
    - Action: applies environment rules, sends feedback
    - Environment: represented via PrisonersDilemmaEnvironment instance
    """

    class MatchRunner(OneShotBehaviour):
        def __init__(self, rounds, T, R, P, S, player1_jid, player2_jid, results_list, result_callback):
            super().__init__()
            # --- Environment ---
            self.environment = PrisonersDilemmaEnvironment(T=T, R=R, P=P, S=S)
            self.total_rounds = rounds

            # --- Agent Identification ---
            self.player1_jid = str(player1_jid).split("/")[0]  # bare JID
            self.player2_jid = str(player2_jid).split("/")[0]  # bare JID

            # --- Internal State (Deliberative Memory) ---
            self.history = []  # stores all round outcomes
            self.results_list = results_list
            self.result_callback = result_callback

        async def run(self):
            for round_idx in range(1, self.total_rounds + 1):
                # === PERCEPTION: Request actions from players ===
                for jid in [self.player1_jid, self.player2_jid]:
                    req = Message(to=jid)
                    req.set_metadata("performative", "request")
                    req.set_metadata("ontology", "REQUEST_ACTION")
                    await self.send(req)

                # === PERCEPTION: Receive player actions ===
                action_map = {self.player1_jid: None, self.player2_jid: None}
                for _ in range(2):
                    resp = await self.receive(timeout=3)
                    if resp:
                        sender = str(resp.sender).split("/")[0]
                        if sender in action_map:
                            action_map[sender] = resp.body

                action1 = action_map[self.player1_jid]
                action2 = action_map[self.player2_jid]

                if action1 and action2:
                    # === STATE UPDATE: Deliberative component ===
                    outcome = self.environment.apply_actions(action1, action2)
                    self.history.append(outcome)  # memory of rounds

                    result_entry = {
                        "Round": outcome["round"],
                        "Player1_Action": outcome["p1_action"],
                        "Player1_Payoff": outcome["p1_payoff"],
                        "Player1_ActualPoints": outcome["p1_cumulative"],
                        "Player2_Action": outcome["p2_action"],
                        "Player2_Payoff": outcome["p2_payoff"],
                        "Player2_ActualPoints": outcome["p2_cumulative"]
                    }

                    # Update external reporting if requested
                    if self.results_list is not None:
                        self.results_list.append(result_entry)
                    if self.result_callback:
                        self.result_callback(result_entry)

                    # === ACTION: Feedback to agents ===
                    res_msg1 = Message(to=self.player1_jid)
                    res_msg1.set_metadata("performative", "inform")
                    res_msg1.set_metadata("ontology", "ROUND_RESULT")
                    res_msg1.body = f"{action2},{outcome['p1_payoff']},{outcome['p2_payoff']}"
                    await self.send(res_msg1)

                    res_msg2 = Message(to=self.player2_jid)
                    res_msg2.set_metadata("performative", "inform")
                    res_msg2.set_metadata("ontology", "ROUND_RESULT")
                    res_msg2.body = f"{action1},{outcome['p2_payoff']},{outcome['p1_payoff']}"
                    await self.send(res_msg2)

                else:
                    print(f"[ManagerAgent] Protocol Failure Round {round_idx}: P1={action1}, P2={action2}")

                await asyncio.sleep(0.01)

            # === SUMMARY OF MATCH ===
            print("=== MATCH FINISHED ===")
            print(f"Total Rounds: {self.total_rounds}")
            print(f"Player 1 ({self.player1_jid}) Total Score: {self.environment.total_p1_score}")
            print(f"Player 2 ({self.player2_jid}) Total Score: {self.environment.total_p2_score}")

    def __init__(self, jid, password):
        super().__init__(jid, password, verify_security=False)
        self.match_behaviour = None
        # Internal hybrid state for manager-level strategic coordination
        self.internal_state = {
            "active_matches": [],
            "aggregate_history": []
        }

    async def setup(self):
        print(f"[ManagerAgent] {self.jid} is ready.")

    def start_match(self, rounds, T, R, P, S, p1_jid, p2_jid, results_list, result_callback):
        self.match_behaviour = self.MatchRunner(rounds, T, R, P, S, p1_jid, p2_jid, results_list, result_callback)
        self.add_behaviour(self.match_behaviour)
        # Record active match internally
        self.internal_state["active_matches"].append((p1_jid, p2_jid))