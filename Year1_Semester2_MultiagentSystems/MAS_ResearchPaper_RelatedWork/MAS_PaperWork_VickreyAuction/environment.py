import time
from spade.agent import Agent
from spade.behaviour import State, FSMBehaviour
from spade.message import Message

class AuctioneerAgent(Agent):
    """
    Auctioneer Agent. Acts as the Environment state manager.
    
    🔴 PEAS Model Components for the Environment:
    - Performance measure: Ensure efficient resource allocation where the highest
                           bidder wins and pays the second-highest bid, encouraging
                           truthful bidding.
    - Environment: 
        - Accessible: agents receive complete result information.
        - Deterministic: Vickrey rules are deterministic.
        - Episodic: single auction instance.
        - Static: does not change dynamically independent of actions during the bidding phase.
        - Discrete: distinct bidding and resolution phases.
    - Actuators: Messaging system to send 'cfp' (start auction) and 'inform' (results).
    - Sensors: Messaging system to receive 'propose' (bids) from agents.
    """
    def __init__(self, jid, password, participants):
        super().__init__(jid, password)
        self.participants = participants
        self.bids = {}

    class AuctionFSM(FSMBehaviour):
        async def on_start(self):
            print(f"[{self.agent.name}] FSM Environment initialized.")

        async def on_end(self):
            print(f"[{self.agent.name}] FSM Environment episodic task completed.")

    class CallForProposalState(State):
        async def run(self):
            print(f"[{self.agent.name}] Actuator Action: Sending out CFPs to {len(self.agent.participants)} participants.")
            for participant in self.agent.participants:
                msg = Message(to=participant)
                msg.set_metadata("performative", "cfp")
                msg.body = "Vickrey Auction started. Submit your true valuation."
                await self.send(msg)
            self.set_next_state("ReceiveBids")

    class ReceiveBidsState(State):
        async def run(self):
            print(f"[{self.agent.name}] Sensor Activity: Collecting bids...")
            timeout_duration = 5
            start_time = time.time()
            
            # Wait for bids from all participants or until timeout
            while time.time() - start_time < timeout_duration and len(self.agent.bids) < len(self.agent.participants):
                msg = await self.receive(timeout=1)
                if msg and msg.get_metadata("performative") == "propose":
                    bidder = str(msg.sender).split("/")[0] # Clean JID to base JID
                    bid_value = float(msg.body)
                    self.agent.bids[bidder] = bid_value
                    print(f"[{self.agent.name}] Sensor Action: Perceived bid of {bid_value} from {bidder}")
            
            self.set_next_state("DetermineWinner")

    class DetermineWinnerState(State):
        async def run(self):
            print(f"[{self.agent.name}] Computing Performance Measure (Winner & Price)...")
            if len(self.agent.bids) == 0:
                print(f"[{self.agent.name}] No bids received.")
                self.kill()
                return

            sorted_bids = sorted(self.agent.bids.items(), key=lambda item: item[1], reverse=True)
            
            winner_jid = sorted_bids[0][0]
            winner_bid = sorted_bids[0][1]
            
            # Second highest price (Vickrey Auction rule)
            second_price = sorted_bids[1][1] if len(sorted_bids) > 1 else winner_bid

            print(f"\n--- AUCTION RESULTS ---")
            print(f"Winner: {winner_jid}")
            print(f"Highest Bid (True Valuation): {winner_bid}")
            print(f"Price Paid (2nd Highest): {second_price}")
            print(f"-----------------------\n")

            print(f"[{self.agent.name}] Actuator Action: Informing agents of the results.")
            for participant in self.agent.participants:
                msg = Message(to=participant)
                msg.set_metadata("performative", "inform")
                cleaned_participant = str(participant).split("/")[0]
                
                if cleaned_participant == winner_jid:
                    msg.body = f"YOU WON! You pay {second_price}."
                else:
                    msg.body = f"YOU LOST. Winner pays {second_price}."
                await self.send(msg)
                
            self.kill() # Terminate FSM

    async def setup(self):
        fsm = self.AuctionFSM()
        fsm.add_state(name="CallForProposal", state=self.CallForProposalState(), initial=True)
        fsm.add_state(name="ReceiveBids", state=self.ReceiveBidsState())
        fsm.add_state(name="DetermineWinner", state=self.DetermineWinnerState())
        
        fsm.add_transition(source="CallForProposal", dest="ReceiveBids")
        fsm.add_transition(source="ReceiveBids", dest="DetermineWinner")
        
        self.add_behaviour(fsm)
