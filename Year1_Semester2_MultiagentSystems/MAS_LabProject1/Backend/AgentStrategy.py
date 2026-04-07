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

class HumanStrategy(AgentStrategy):
    """Strategy driven by human input via asyncio Queue."""
    def __init__(self, action_queue):
        super().__init__()
        self.action_queue = action_queue

    async def decide(self, history: list) -> str:
        # Wait for the human to put 'C' or 'D' in the queue
        import asyncio
        import queue
        while True:
            try:
                # non-blocking check
                item = self.action_queue.get_nowait()
                return item
            except queue.Empty:
                await asyncio.sleep(0.1)
