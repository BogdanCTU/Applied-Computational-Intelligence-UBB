import asyncio
from agent import BidderAgent
from environment import AuctioneerAgent

async def main():
    auctioneer_jid = "auctioneer@localhost"
    bidder1_jid = "bidder1@localhost"
    bidder2_jid = "bidder2@localhost"
    bidder3_jid = "bidder3@localhost"
    password = "your_password"
    
    # Instantiate Bidder Agents with true valuations (b_i = v_i)
    # The optimal strategy in Vickrey is to bid true valuation.
    bidder1 = BidderAgent(bidder1_jid, password, true_valuation=150.0)
    bidder2 = BidderAgent(bidder2_jid, password, true_valuation=220.0)
    bidder3 = BidderAgent(bidder3_jid, password, true_valuation=180.0)
    
    # Participants List
    participants = [bidder1_jid, bidder2_jid, bidder3_jid]
    
    # Instantiate Auctioneer (Environment Manager)
    auctioneer = AuctioneerAgent(auctioneer_jid, password, participants)
    
    # Start bidders
    print("Starting agents...")
    await bidder1.start(auto_register=True)
    await bidder2.start(auto_register=True)
    await bidder3.start(auto_register=True)
    
    # Give bidders time to start and connect to the XMPP server
    await asyncio.sleep(2)
    
    # Start auctioneer
    await auctioneer.start(auto_register=True)
    
    # Wait until auction FSM completes
    while auctioneer.is_alive():
        await asyncio.sleep(1)
        
    await asyncio.sleep(2) # Give time for INFORMs to arrive at bidders
    
    # Stop agents
    await bidder1.stop()
    await bidder2.stop()
    await bidder3.stop()
    await auctioneer.stop()
    print("System shutdown.")

if __name__ == "__main__":
    asyncio.run(main())
