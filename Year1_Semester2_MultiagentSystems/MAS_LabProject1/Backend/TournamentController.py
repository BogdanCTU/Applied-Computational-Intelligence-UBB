import asyncio
import threading
from ManagerAgent import ManagerAgent
from PlayerAgent import PlayerAgent
from AgentStrategy import RandomStrategy, TitForTat, AlwaysCooperate, AlwaysDefect
from server_config import XMPP_SERVER, PASSWORD

class TournamentController:
    def __init__(self, update_callback=None, completion_callback=None):
        self.update_callback = update_callback
        self.completion_callback = completion_callback
        self.results_list = []
        self.is_running = False
        self._thread = None
        self._loop = None
        
        self.agents = []
        self.manager = None

    def start_tournament(self, num_agents, num_matches, rounds, T, R, P, S, strategy_list):
        if self.is_running:
            return
            
        self.is_running = True
        self.results_list.clear()
        
        self._thread = threading.Thread(target=self._run_async_loop, args=(num_agents, num_matches, rounds, T, R, P, S, strategy_list), daemon=True)
        self._thread.start()
        
    def stop_tournament(self):
        if not self.is_running:
            return
        self.is_running = False
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._stop_agents(), self._loop)

    def _run_async_loop(self, num_agents, num_matches, rounds, T, R, P, S, strategy_list):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_simulation(num_agents, num_matches, rounds, T, R, P, S, strategy_list))
        except Exception as e:
            print(f"Async loop exception: {e}")
        finally:
            self.is_running = False
            self._loop.close()
            if self.completion_callback:
                self.completion_callback()

    async def _stop_agents(self):
        for agent in self.agents:
            await agent.stop()
        if self.manager: await self.manager.stop()
        
    async def _async_simulation(self, num_agents, num_matches, rounds, T, R, P, S, strategy_list):
        xmpp_server = XMPP_SERVER 
        password = PASSWORD

        strategy_map = {
            "TitForTat": TitForTat,
            "RandomStrategy": RandomStrategy,
            "AlwaysCooperate": AlwaysCooperate,
            "AlwaysDefect": AlwaysDefect
        }

        # Spawn agents
        self.agents = []
        for i in range(num_agents):
            jid = f"agent_{i}@{xmpp_server}"
            strat_name = strategy_list[i % len(strategy_list)]
            agent = PlayerAgent(jid, password, strategy=strategy_map.get(strat_name, RandomStrategy)())
            self.agents.append(agent)

        gm_jid = f"manager_tournament@{xmpp_server}"
        self.manager = ManagerAgent(gm_jid, password)

        try:
            for agent in self.agents:
                await agent.start(auto_register=True)
            await self.manager.start(auto_register=True)
        except Exception as e:
            print(f"Agent Start Failed: {e}")
            self.is_running = False
            return
            
        await asyncio.sleep(2)
        
        # Run matches: each plays against every other
        for i in range(num_agents):
            for j in range(i+1, num_agents):
                for match_idx in range(num_matches):
                    if not self.is_running:
                        break
                    
                    # Update callback could include meta-info, but we'll adapt results_list
                    match_meta = {"MatchID": f"{i}vs{j}_m{match_idx}", "P1": f"agent_{i}", "P2": f"agent_{j}"}

                    def wrap_callback(result_entry):
                        full_entry = dict(match_meta, **result_entry)
                        self.results_list.append(full_entry)
                        if self.update_callback:
                            self.update_callback(full_entry)
                            
                    self.manager.start_match(rounds, T, R, P, S, self.agents[i].jid, self.agents[j].jid, [], wrap_callback)
                    
                    # Wait for this specific match to complete
                    try:
                        while not self.manager.match_behaviour.is_killed and self.is_running:
                            await asyncio.sleep(0.1)
                        if self.is_running:
                            await self.manager.match_behaviour.join()
                    except Exception as e:
                        print(f"Tournament Match interrupted: {e}")

        await self._stop_agents()

    def get_results(self):
        return self.results_list
