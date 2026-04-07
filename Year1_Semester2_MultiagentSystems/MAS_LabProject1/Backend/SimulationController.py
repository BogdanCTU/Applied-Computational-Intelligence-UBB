import asyncio
import threading
from ManagerAgent import ManagerAgent
from PlayerAgent import PlayerAgent
from AgentStrategy import RandomStrategy, TitForTat, AlwaysCooperate, AlwaysDefect

class SimulationController:
    def __init__(self, update_callback=None, completion_callback=None):
        self.update_callback = update_callback
        self.completion_callback = completion_callback
        self.results_list = []
        self.is_running = False
        self._thread = None
        self._loop = None
        
        self.player1 = None
        self.player2 = None
        self.manager = None

    def start_simulation(self, rounds, T, R, P, S, p1_strat="TitForTat", p2_strat="RandomStrategy"):
        if self.is_running:
            return
            
        self.is_running = True
        self.results_list.clear()
        
        # Start a new thread for the asyncio loop
        self._thread = threading.Thread(target=self._run_async_loop, args=(rounds, T, R, P, S, p1_strat, p2_strat), daemon=True)
        self._thread.start()
        
    def stop_simulation(self):
        if not self.is_running:
            return
        self.is_running = False
        if self._loop:
            # Schedule the stop agents concurrently so we don't block the GUI
            asyncio.run_coroutine_threadsafe(self._stop_agents(), self._loop)

    def _run_async_loop(self, rounds, T, R, P, S, p1_strat, p2_strat):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_simulation(rounds, T, R, P, S, p1_strat, p2_strat))
        except Exception as e:
            print(f"Async loop exception: {e}")
        finally:
            self.is_running = False
            self._loop.close()
            if self.completion_callback:
                self.completion_callback()

    async def _stop_agents(self):
        if self.player1: await self.player1.stop()
        if self.player2: await self.player2.stop()
        if self.manager: await self.manager.stop()
        
    async def _async_simulation(self, rounds, T, R, P, S, p1_strat, p2_strat):
        xmpp_server = "bogdanpc" 
        password = "admin"

        p1_jid = f"player1@{xmpp_server}"
        p2_jid = f"player2@{xmpp_server}"
        gm_jid = f"manager@{xmpp_server}"

        strategy_map = {
            "TitForTat": TitForTat,
            "RandomStrategy": RandomStrategy,
            "AlwaysCooperate": AlwaysCooperate,
            "AlwaysDefect": AlwaysDefect
        }

        self.player1 = PlayerAgent(p1_jid, password, strategy=strategy_map.get(p1_strat, TitForTat)())
        self.player2 = PlayerAgent(p2_jid, password, strategy=strategy_map.get(p2_strat, RandomStrategy)())
        self.manager = ManagerAgent(gm_jid, password)

        try:
            await self.player1.start(auto_register=True)
            await self.player2.start(auto_register=True)
            await self.manager.start(auto_register=True)
        except Exception as e:
            print(f"Agent Start Failed: {e}")
            self.is_running = False
            return
            
        # Give agents a moment to fully register and prepare
        await asyncio.sleep(2)
        
        if not self.is_running:
            await self._stop_agents()
            return
            
        self.manager.start_match(rounds, T, R, P, S, p1_jid, p2_jid, self.results_list, self.on_round_completed)

        if self.manager.match_behaviour:
            # We wait for the behaviour to cleanly join if it completes normally
            try:
                # Running a task that we can cancel if stop is requested
                # or just joining it and relying on the XMPP connections dying when stop() is called.
                while not self.manager.match_behaviour.is_killed and self.is_running:
                    await asyncio.sleep(0.1)
                
                # if still running, implies we finished normally
                if self.is_running:
                     await self.manager.match_behaviour.join()
            except Exception as e:
                print(f"Match interrupted: {e}")

        await self._stop_agents()

    def on_round_completed(self, result_entry):
        if self.update_callback:
            self.update_callback(result_entry)
            
    def get_results(self):
        return self.results_list
