from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

class BidderAgent(Agent):
    """
    Bidder Agent designed using the PAGE model.
    
    🔴 PAGE Model Components for Bidder:
    - Perception: Receives 'cfp' (Call for Proposal) messages containing auction details
                  and 'inform' messages with the auction results.
    - Action: Submits 'propose' messages containing the bid value (true valuation).
    - Goal: Participate efficiently in the Vickrey auction by bidding its true valuation
            (b_i = v_i) to maximize its utility without overpaying.
    - Environment: The multi-agent auction environment, handled by the Auctioneer, 
                   which receives bids and applies Vickrey rules.
    """
    def __init__(self, jid, password, true_valuation):
        super().__init__(jid, password)
        self.true_valuation = true_valuation

    class BidBehaviour(CyclicBehaviour):
        async def run(self):
            # Perception: Wait for state updates from the environment
            msg = await self.receive(timeout=10)
            if msg:
                performative = msg.get_metadata("performative")
                # Action & Goal: Act based on the perception
                if performative == "cfp":
                    print(f"[{self.agent.name}] Perceived CFP. Action: Bidding true valuation ({self.agent.true_valuation}).")
                    reply = Message(to=str(msg.sender))
                    reply.set_metadata("performative", "propose")
                    reply.body = str(self.agent.true_valuation)
                    await self.send(reply)
                
                elif performative == "inform":
                    print(f"[{self.agent.name}] Perceived Auction Result: {msg.body}")
                    self.kill()

    async def setup(self):
        # We start the BidBehaviour when the agent starts
        self.add_behaviour(self.BidBehaviour())
