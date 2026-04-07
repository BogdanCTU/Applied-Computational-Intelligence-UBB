import random

class AgentStrategy:
    """Base category of the strategies usable by Player Agents."""
    
    def __init__(self):
        pass

    def decide(self, history: list) -> str:
        """
        Determines the move given the historical interactions.
        :param history: list of tuples (my_move, opponent_move)
        :return: 'C' or 'D'
        """
        raise NotImplementedError("Subclasses must implement `decide` method.")

class RandomStrategy(AgentStrategy):
    """Randomly decides to Cooperate or Defect."""
    def decide(self, history: list) -> str:
        return random.choice(["C", "D"])

class AlwaysCooperate(AgentStrategy):
    """Always Cooperates."""
    def decide(self, history: list) -> str:
        return "C"

class AlwaysDefect(AgentStrategy):
    """Always Defects."""
    def decide(self, history: list) -> str:
        return "D"

class TitForTat(AgentStrategy):
    """Cooperates initially, then repeats the opponent's last move."""
    def decide(self, history: list) -> str:
        if not history:
            return "C"  # Initial move
        # The opponent's last move is the second element of the last tuple
        return history[-1][1]
