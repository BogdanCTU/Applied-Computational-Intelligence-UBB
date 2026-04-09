import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from AgentStrategy import AgentStrategy as Strategy

class PlayerAgent(Agent):
    """
    Hybrid Architecture Agent based on the PAGE Model and Vertical Layering.
    
    Architectural Layers:
    1. Perception Subsystem: Maps environment states to internal percepts.
    2. Reactive Layer (Bottom): Handles immediate stimuli and execution cycle.
    3. Deliberative Layer (Top): Maintains state/history and reasons using strategy.
    
    Execution Cycle: Observe -> Update State -> Select Action -> Execute.
    """

    class PlayBehaviour(CyclicBehaviour):
        async def run(self):
            # --- 1. Perception (Sense) ---
            msg = await self.receive(timeout=1.0)
            if msg:
                ontology = msg.metadata.get("ontology")
                
                # --- 2. Reactive / Deliberative Trigger ---
                if ontology == "REQUEST_ACTION":
                    # Deliberative reasoning
                    choice = await self.agent.deliberate_cycle()
                    
                    # --- 4. Action Execution ---
                    # Use the behaviour's send method which is the standard in SPADE
                    await self.agent.execute_action(choice, str(msg.sender), self)
                    
                elif ontology == "ROUND_RESULT":
                    # Perception -> State update
                    await self.agent.process_percept(msg.body)

    def __init__(self, jid, password, strategy: Strategy):
        super().__init__(jid, password, verify_security=False)
        self.strategy = strategy
        self.history = []  
        self.last_choice = None
        self.total_score = 0
        self.goal = "Maximize cumulative payoff through strategic reasoning"

    async def setup(self):
        self.add_behaviour(self.PlayBehaviour())

    async def deliberate_cycle(self):
        """
        Deliberative logic: internal state-update and action mapping.
        """
        choice_result = self.strategy.decide(self.history)
        if asyncio.iscoroutine(choice_result):
            choice = await choice_result
        else:
            choice = choice_result
        
        self.last_choice = choice
        return choice

    async def execute_action(self, choice, target_jid, behaviour):
        """
        Translation of decision to environmental effect.
        Note: SPADE requires using a behaviour's 'send' method.
        """
        reply = Message(to=target_jid)
        reply.set_metadata("performative", "inform")
        reply.set_metadata("ontology", "ACTION_RESPONSE")
        reply.body = choice
        # The behaviour instance is responsible for the actual message transport
        await behaviour.send(reply)

    async def process_percept(self, percept_body):
        """
        State-Update Function: Maps percept and old state to a new state.
        """
        details = percept_body.split(",")
        if len(details) >= 2:
            opponent_choice = details[0]
            try:
                my_payoff = int(details[1])
            except ValueError:
                my_payoff = 0
            
            # Updating the internal memory (State)
            self.history.append((self.last_choice, opponent_choice))
            self.total_score += my_payoff
