import asyncio

class PrisonersDilemmaEnvironment:
    """
    Representation of the Prisoner's Dilemma Environment following the PEAS and PAGE(S) models.
    
    PEAS Model:
    - Performance Measure: Cumulative payoff based on the T, R, P, S matrix.
    - Environment: A discrete, sequential interaction space between two autonomous agents.
    - Actuators: Action selection mechanism (Cooperate 'C' or Defect 'D').
    - Sensors: Perception of match state (opponent's move, round results, scores).
    
    Environmental Properties (Formal Classification):
    - Inaccessible: Agents have no direct access to the internal state or strategy of the opponent.
    - Non-deterministic: The next state is a result of two independent concurrent decisions.
    - Sequential: Current actions impact future states and the opponent's reactive behavior.
    - Static: The state only changes when agents act.
    - Discrete: The action space A = {'C', 'D'} and state space S are finite.
    - Non-Markovian: Future state outcomes (opponent moves) are typically modeled on history rather than just the last state.
    
    Mathematical View:
    - S (States): Set of possible match histories.
    - A (Actions): {'C', 'D'}.
    """


    def __init__(self, T=5, R=3, P=1, S=0):
        # Payoff matrix parameters (T > R > P > S)
        self.T = T  # Temptation
        self.R = R  # Reward
        self.P = P  # Punishment
        self.S = S  # Sucker's payoff
        
        # S: The set of states is represented by the match history and current totals
        self.history = []  
        self.current_round = 0
        self.total_p1_score = 0
        self.total_p2_score = 0

        # --- Enhanced Internal State for Hybrid/Deliberative Reasoning ---
        self.last_actions = {"p1": None, "p2": None}         # Reactive reference
        self.cumulative_actions = {"p1": [], "p2": []}       # For planning/pattern recognition
        self.last_payoffs = {"p1": 0, "p2": 0}               # Immediate feedback for reactive layer
        self.total_scores = {"p1": 0, "p2": 0}               # Redundant tracking for clarity


    @property
    def action_space(self):
        """A = {a1, a2, ...}"""
        return {'C', 'D'}


    def get_state(self):
        """Returns the current environment state s_i."""
        return {
            "round": self.current_round,
            "total_p1": self.total_p1_score,
            "total_p2": self.total_p2_score,
            "history": self.history
        }


    def get_payoffs(self, action1, action2):
        """The environment behavior function: matches (s, a) to outcomes."""
        if action1 == "C" and action2 == "C":
            return (self.R, self.R)
        elif action1 == "D" and action2 == "D":
            return (self.P, self.P)
        elif action1 == "C" and action2 == "D":
            return (self.S, self.T)
        elif action1 == "D" and action2 == "C":
            return (self.T, self.S)
        return (0, 0)


    def apply_actions(self, action1, action2):
        self.current_round += 1
        p1_payoff, p2_payoff = self.get_payoffs(action1, action2)

        # Update scores
        self.total_p1_score += p1_payoff
        self.total_p2_score += p2_payoff

        # Update enhanced internal state
        self.last_actions.update({"p1": action1, "p2": action2})
        self.cumulative_actions["p1"].append(action1)
        self.cumulative_actions["p2"].append(action2)
        self.last_payoffs.update({"p1": p1_payoff, "p2": p2_payoff})
        self.total_scores.update({"p1": self.total_p1_score, "p2": self.total_p2_score})

        result = {
            "round": self.current_round,
            "p1_action": action1,
            "p2_action": action2,
            "p1_payoff": p1_payoff,
            "p2_payoff": p2_payoff,
            "p1_cumulative": self.total_p1_score,
            "p2_cumulative": self.total_p2_score
        }
        self.history.append(result)
        return result
        

    def get_percept(self, player_index):
        """
        Perception Subsystem: mapping environment states to percepts for agents.
        """
        if not self.history:
            return {
                "opponent_last_action": None,
                "my_last_action": None,
                "my_payoff": 0,
                "total_score": 0
            }
        
        last_round = self.history[-1]
        if player_index == 1:
            return {
                "opponent_last_action": last_round["p2_action"],
                "my_last_action": last_round["p1_action"],
                "my_payoff": last_round["p1_payoff"],
                "total_score": self.total_p1_score
            }
        else:
            return {
                "opponent_last_action": last_round["p1_action"],
                "my_last_action": last_round["p2_action"],
                "my_payoff": last_round["p2_payoff"],
                "total_score": self.total_p2_score
            }