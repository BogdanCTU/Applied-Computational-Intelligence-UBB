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

class GrimTrigger(AgentStrategy):
    """Cooperates until opponent defects once, then always defects."""
    def decide(self, history: list) -> str:
        if any(move[1] == "D" for move in history):
            return "D"
        return "C"

class TitForTwoTats(AgentStrategy):
    """Cooperates unless opponent defects twice in a row."""
    def decide(self, history: list) -> str:
        if len(history) < 2:
            return "C"
        if history[-1][1] == "D" and history[-2][1] == "D":
            return "D"
        return "C"

class Pavlov(AgentStrategy):
    """Repeats last move if rewarded, switches if punished."""
    def decide(self, history: list) -> str:
        if not history:
            return "C"
        last_my, last_opp = history[-1]
        # Reward = both cooperate or both defect
        if last_my == last_opp:
            return last_my
        return "D" if last_my == "C" else "C"

class RandomCooperate(AgentStrategy):
    """Randomly cooperates with probability p."""
    def __init__(self, p=0.5):
        self.p = p
    def decide(self, history: list) -> str:
        return "C" if random.random() < self.p else "D"

class Alternator(AgentStrategy):
    """Alternates between Cooperate and Defect."""
    def decide(self, history: list) -> str:
        return "C" if len(history) % 2 == 0 else "D"

class SoftMajority(AgentStrategy):
    """Cooperates if opponent cooperated more than defected."""
    def decide(self, history: list) -> str:
        if not history:
            return "C"
        coop = sum(1 for _, opp in history if opp == "C")
        defe = sum(1 for _, opp in history if opp == "D")
        return "C" if coop >= defe else "D"

class HardMajority(AgentStrategy):
    """Defects if opponent defected more than cooperated."""
    def decide(self, history: list) -> str:
        if not history:
            return "C"
        coop = sum(1 for _, opp in history if opp == "C")
        return "D" if coop < len(history)/2 else "C"

class SuspiciousTitForTat(AgentStrategy):
    """Defects on first move, then mimics opponent."""
    def decide(self, history: list) -> str:
        if not history:
            return "D"
        return history[-1][1]

class TwoTitsForTat(AgentStrategy):
    """Defects only if opponent defects twice consecutively."""
    def decide(self, history: list) -> str:
        if len(history) < 2:
            return "C"
        if history[-1][1] == "D" and history[-2][1] == "D":
            return "D"
        return "C"

class Prober(AgentStrategy):
    """Defects on first move, cooperates if opponent retaliates, else defects."""
    def decide(self, history: list) -> str:
        if not history:
            return "D"
        if len(history) == 1:
            return "C" if history[0][1] == "D" else "D"
        return history[-1][1]

class ForgivingTitForTat(AgentStrategy):
    """Occasionally forgives a defection to restore cooperation."""
    def __init__(self, forgive_prob=0.1):
        self.forgive_prob = forgive_prob
    def decide(self, history: list) -> str:
        if not history:
            return "C"
        last = history[-1][1]
        if last == "D" and random.random() < self.forgive_prob:
            return "C"
        return last

class Adaptive(AgentStrategy):
    """Adjusts cooperation probability based on opponent's history."""
    def decide(self, history: list) -> str:
        if not history:
            return "C"
        coop_ratio = sum(1 for _, opp in history if opp == "C") / len(history)
        return "C" if random.random() < coop_ratio else "D"

class Spiteful(AgentStrategy):
    """Defects if opponent ever defects, otherwise cooperates."""
    def decide(self, history: list) -> str:
        if any(move[1] == "D" for move in history):
            return "D"
        return "C"

class GenerousTitForTat(AgentStrategy):
    """Mimics opponent but occasionally cooperates after opponent defects."""
    def __init__(self, gen_prob=0.2):
        self.gen_prob = gen_prob
    def decide(self, history: list) -> str:
        if not history:
            return "C"
        last = history[-1][1]
        if last == "D" and random.random() < self.gen_prob:
            return "C"
        return last

class TitForTatWithNoise(AgentStrategy):
    """Acts like Tit-for-Tat but sometimes flips choice randomly."""
    def __init__(self, noise_prob=0.05):
        self.noise_prob = noise_prob
    def decide(self, history: list) -> str:
        if random.random() < self.noise_prob:
            return "D" if random.random() < 0.5 else "C"
        if not history:
            return "C"
        return history[-1][1]

class WinStayLoseShift(AgentStrategy):
    """Pavlov variant: stays if payoff good, shifts if bad."""
    def decide(self, history: list) -> str:
        if not history:
            return "C"
        last_my, last_opp = history[-1]
        if last_my == last_opp:
            return last_my  # reward, stay
        return "D" if last_my == "C" else "C"

class TitForTatWithMemory(AgentStrategy):
    """Considers last n opponent moves to decide."""
    def __init__(self, n=3):
        self.n = n
    def decide(self, history: list) -> str:
        if not history:
            return "C"
        recent = history[-self.n:]
        if any(move[1] == "D" for move in recent):
            return "D"
        return "C"

class Detective(AgentStrategy):
    """Probes opponent with specific sequence then adapts."""
    def __init__(self):
        self.probe_seq = ["C", "D", "C", "C"]
    def decide(self, history: list) -> str:
        if len(history) < len(self.probe_seq):
            return self.probe_seq[len(history)]
        if any(move[1] == "D" for move in history[:4]):
            return TitForTat().decide(history)
        return "D"

class TitForTatWithDelay(AgentStrategy):
    """Ignores the last k opponent moves before responding."""
    def __init__(self, delay=1):
        self.delay = delay
    def decide(self, history: list) -> str:
        if len(history) <= self.delay:
            return "C"
        return history[-self.delay-1][1]

class ContriteTitForTat(AgentStrategy):
    """Tries to repair accidental defections by cooperating after self-defect."""
    def decide(self, history: list) -> str:
        if not history:
            return "C"
        last_my, last_opp = history[-1]
        if last_my == "D" and last_opp == "C":
            return "C"
        return last_opp