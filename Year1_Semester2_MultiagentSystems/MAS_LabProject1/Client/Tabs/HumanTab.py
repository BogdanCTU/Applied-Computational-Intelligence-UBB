import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import queue
from HumanGameController import HumanGameController

class HumanTab(ttk.Frame):
    def __init__(self, parent, sys_root):
        super().__init__(parent)
        self.sys_root = sys_root
        
        self.action_queue = queue.Queue()
        self.update_queue = queue.Queue()
        self.controller = HumanGameController(
            action_queue=self.action_queue,
            update_callback=self.on_round_update,
            completion_callback=self.on_simulation_complete
        )
        self.pack(fill=tk.BOTH, expand=True)
        self.setup_ui()
        self.sys_root.after(100, self.process_queue)

    def setup_ui(self):
        control_frame = ttk.LabelFrame(self, text="Human vs Agent Parameters")
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(control_frame, text="Rounds:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.rounds_var = tk.IntVar(value=10)
        ttk.Entry(control_frame, textvariable=self.rounds_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(control_frame, text="T (Temptation):").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.t_var = tk.IntVar(value=5)
        ttk.Entry(control_frame, textvariable=self.t_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(control_frame, text="R (Reward):").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.r_var = tk.IntVar(value=3)
        ttk.Entry(control_frame, textvariable=self.r_var, width=10).grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(control_frame, text="P (Punishment):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.p_var = tk.IntVar(value=1)
        ttk.Entry(control_frame, textvariable=self.p_var, width=10).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(control_frame, text="S (Sucker):").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.s_var = tk.IntVar(value=0)
        ttk.Entry(control_frame, textvariable=self.s_var, width=10).grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(control_frame, text="Agent Strategy:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.bot_strat_var = tk.StringVar(value="TitForTat")
        ttk.Combobox(control_frame, textvariable=self.bot_strat_var, values=["TitForTat", "RandomStrategy", "AlwaysCooperate", "AlwaysDefect"], state="readonly", width=15).grid(row=2, column=1, padx=5, pady=5)

        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=0, column=6, rowspan=3, padx=20, pady=5)

        self.btn_start = ttk.Button(btn_frame, text="Start Game", command=self.start_sim)
        self.btn_start.pack(fill=tk.X, pady=2)

        self.btn_stop = ttk.Button(btn_frame, text="Stop Game", command=self.stop_sim, state=tk.DISABLED)
        self.btn_stop.pack(fill=tk.X, pady=2)

        self.btn_export = ttk.Button(control_frame, text="Export CSV", command=self.export_csv)
        self.btn_export.grid(row=1, column=4, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # Human Interaction Frame
        play_frame = ttk.LabelFrame(self, text="Your Move")
        play_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.btn_coop = ttk.Button(play_frame, text="Cooperate (C)", command=lambda: self.make_move("C"), state=tk.DISABLED)
        self.btn_coop.pack(side=tk.LEFT, padx=10, pady=10, expand=True, fill=tk.X)
        
        self.btn_def = ttk.Button(play_frame, text="Defect (D)", command=lambda: self.make_move("D"), state=tk.DISABLED)
        self.btn_def.pack(side=tk.LEFT, padx=10, pady=10, expand=True, fill=tk.X)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = (
            "Round", "You", "Your_Payoff", "Your_Points",
            "Agent", "Agent_Payoff", "Agent_Points"
        )
        
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_y.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

    def start_sim(self):
        try:
            rnds = self.rounds_var.get()
            t = self.t_var.get()
            r = self.r_var.get()
            p = self.p_var.get()
            s = self.s_var.get()
            bot_strat = self.bot_strat_var.get()
        except tk.TclError:
            messagebox.showerror("Error", "Please enter valid integers.")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        # Clear queue
        while not self.action_queue.empty(): self.action_queue.get()
        
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_coop.config(state=tk.NORMAL)
        self.btn_def.config(state=tk.NORMAL)
        
        self.controller.start_game(rnds, t, r, p, s, bot_strat)

    def stop_sim(self):
        self.controller.stop_game()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_coop.config(state=tk.DISABLED)
        self.btn_def.config(state=tk.DISABLED)

    def make_move(self, move):
        self.controller.submit_action(move)

    def on_round_update(self, entry):
        self.update_queue.put(entry)

    def on_simulation_complete(self):
        self.update_queue.put("SIM_COMPLETE")

    def process_queue(self):
        try:
            while True:
                item = self.update_queue.get_nowait()
                if item == "SIM_COMPLETE":
                    self.stop_sim()
                    messagebox.showinfo("Game Over", "Match Finished.")
                else:
                    values = (
                        item["Round"], item["Player1_Action"], item["Player1_Payoff"], item["Player1_ActualPoints"],
                        item["Player2_Action"], item["Player2_Payoff"], item["Player2_ActualPoints"]
                    )
                    self.tree.insert("", tk.END, values=values)
                    self.tree.yview_moveto(1)
                self.update_queue.task_done()
        except queue.Empty:
            pass
        self.sys_root.after(100, self.process_queue)

    def export_csv(self):
        results = self.controller.get_results()
        if not results: return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if file_path:
            with open(file_path, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Round", "You", "Your_Payoff", "Your_Points", "Agent", "Agent_Payoff", "Agent_Points"])
                for res in results:
                    writer.writerow([res["Round"], res["Player1_Action"], res["Player1_Payoff"], res["Player1_ActualPoints"], res["Player2_Action"], res["Player2_Payoff"], res["Player2_ActualPoints"]])
            messagebox.showinfo("Export", f"Exported to {file_path}")

    def destroy_tab(self):
        self.controller.stop_game()
