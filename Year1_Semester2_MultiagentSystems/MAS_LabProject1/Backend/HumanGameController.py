import asyncio
import threading
from ManagerAgent import ManagerAgent
from PlayerAgent import PlayerAgent
from AgentStrategy import RandomStrategy, TitForTat, AlwaysCooperate, AlwaysDefect, HumanStrategy

class HumanGameController:
    def __init__(self, action_queue, update_callback=None, completion_callback=None):
        self.action_queue = action_queue
        self.update_callback = update_callback
        self.completion_callback = completion_callback
        self.results_list = []
        self.is_running = False
        self._thread = None
        self._loop = None
        
        self.human_agent = None
        self.bot_agent = None
        self.manager = None

    def start_game(self, rounds, T, R, P, S, bot_strat_name):
        if self.is_running:
            return
            
        self.is_running = True
        self.results_list.clear()
        
        self._thread = threading.Thread(target=self._run_async_loop, args=(rounds, T, R, P, S, bot_strat_name), daemon=True)
        self._thread.start()

    def submit_action(self, action):
        self.action_queue.put(action)

    def stop_game(self):
        if not self.is_running:
            return
        self.is_running = False
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._stop_agents(), self._loop)

    def _run_async_loop(self, rounds, T, R, P, S, bot_strat):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_simulation(rounds, T, R, P, S, bot_strat))
        except Exception as e:
            print(f"Async loop exception: {e}")
        finally:
            self.is_running = False
            self._loop.close()
            if self.completion_callback:
                self.completion_callback()

    async def _stop_agents(self):
        if self.human_agent: await self.human_agent.stop()
        if self.bot_agent: await self.bot_agent.stop()
        if self.manager: await self.manager.stop()
        
    async def _async_simulation(self, rounds, T, R, P, S, bot_strat):
        xmpp_server = "bogdanpc" 
        password = "admin"

        h_jid = f"human@{xmpp_server}"
        b_jid = f"bot@{xmpp_server}"
        gm_jid = f"manager_human@{xmpp_server}"

        strategy_map = {
            "TitForTat": TitForTat,
            "RandomStrategy": RandomStrategy,
            "AlwaysCooperate": AlwaysCooperate,
            "AlwaysDefect": AlwaysDefect
        }

        self.human_agent = PlayerAgent(h_jid, password, strategy=HumanStrategy(self.action_queue))
        self.bot_agent = PlayerAgent(b_jid, password, strategy=strategy_map.get(bot_strat, RandomStrategy)())
        self.manager = ManagerAgent(gm_jid, password)

        try:
            await self.human_agent.start(auto_register=True)
            await self.bot_agent.start(auto_register=True)
            await self.manager.start(auto_register=True)
        except Exception as e:
            print(f"Agent Start Failed: {e}")
            self.is_running = False
            return
            
        await asyncio.sleep(2)
        
        if not self.is_running:
            await self._stop_agents()
            return
            
        self.manager.start_match(rounds, T, R, P, S, h_jid, b_jid, self.results_list, self.on_round_completed)

        if self.manager.match_behaviour:
            try:
                while not self.manager.match_behaviour.is_killed and self.is_running:
                    await asyncio.sleep(0.1)
                
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
