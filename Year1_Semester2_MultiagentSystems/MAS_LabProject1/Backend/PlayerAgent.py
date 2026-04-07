import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

from AgentStrategy import AgentStrategy as Strategy

class PlayerAgent(Agent):
    """
    Autonomous Player Entity. 
    Listens for 'REQUEST_ACTION' from the manager and responds with 'C' or 'D'.
    It also receives previous round result context to record history and update strategy logic.
    """
    
    class PlayBehaviour(CyclicBehaviour):
        async def run(self):
            # Await any message request (actions or results)
            msg = await self.receive(timeout=1.0)
            if msg:
                ontology = msg.metadata.get("ontology")
                if ontology == "REQUEST_ACTION":
                    # Time to make a move
                    choice_result = self.agent.strategy.decide(self.agent.history)
                    if asyncio.iscoroutine(choice_result):
                        choice = await choice_result
                    else:
                        choice = choice_result
                    self.agent.last_choice = choice
                    
                    reply = Message(to=str(msg.sender))
                    reply.set_metadata("performative", "inform")
                    reply.set_metadata("ontology", "ACTION_RESPONSE")
                    reply.body = choice
                    await self.send(reply)
                    
                elif ontology == "ROUND_RESULT":
                    # The manager tells us what the opponent played and points awarded
                    # Body format expected: "OPPONENT_CHOICE,MY_PAYOFF,OPPONENT_PAYOFF"
                    details = msg.body.split(",")
                    if len(details) >= 1:
                        opponent_choice = details[0]
                        # Append the interaction outcome to internal history
                        self.agent.history.append((self.agent.last_choice, opponent_choice))
                        
    def __init__(self, jid, password, strategy: Strategy):
        super().__init__(jid, password)
        self.strategy = strategy
        self.history = []  # List of tuples (my_choice, opponent_choice)
        self.last_choice = None

    async def setup(self):
        b = self.PlayBehaviour()
        self.add_behaviour(b)
