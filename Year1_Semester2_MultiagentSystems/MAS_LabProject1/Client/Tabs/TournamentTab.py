import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import queue
from TournamentController import TournamentController

class TournamentTab(ttk.Frame):
    def __init__(self, parent, sys_root):
        super().__init__(parent)
        self.sys_root = sys_root
        
        self.update_queue = queue.Queue()
        self.controller = TournamentController(
            update_callback=self.on_match_update,
            completion_callback=self.on_simulation_complete
        )
        self.pack(fill=tk.BOTH, expand=True)
        self.setup_ui()
        self.sys_root.after(100, self.process_queue)

    def setup_ui(self):
        control_frame = ttk.LabelFrame(self, text="Tournament Parameters")
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(control_frame, text="Agents # :").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.agents_var = tk.IntVar(value=10)
        ttk.Entry(control_frame, textvariable=self.agents_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(control_frame, text="Matches / pair :").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.matches_var = tk.IntVar(value=1)
        ttk.Entry(control_frame, textvariable=self.matches_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(control_frame, text="Rounds / match :").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.rounds_var = tk.IntVar(value=50)
        ttk.Entry(control_frame, textvariable=self.rounds_var, width=10).grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(control_frame, text="T (Temptation):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.t_var = tk.IntVar(value=5)
        ttk.Entry(control_frame, textvariable=self.t_var, width=10).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(control_frame, text="R (Reward):").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.r_var = tk.IntVar(value=3)
        ttk.Entry(control_frame, textvariable=self.r_var, width=10).grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(control_frame, text="P (Punish):").grid(row=1, column=4, padx=5, pady=5, sticky=tk.W)
        self.p_var = tk.IntVar(value=1)
        ttk.Entry(control_frame, textvariable=self.p_var, width=10).grid(row=1, column=5, padx=5, pady=5)

        ttk.Label(control_frame, text="S (Sucker):").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.s_var = tk.IntVar(value=0)
        ttk.Entry(control_frame, textvariable=self.s_var, width=10).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(control_frame, text="StrategiesPool:").grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)
        
        pool_frame = ttk.Frame(control_frame)
        pool_frame.grid(row=2, column=3, columnspan=3, sticky=tk.NSEW)
        
        scrollbar = ttk.Scrollbar(pool_frame, orient=tk.VERTICAL)
        self.strat_listbox = tk.Listbox(pool_frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set, height=4, exportselection=False)
        scrollbar.config(command=self.strat_listbox.yview)
        
        self.all_strats = [
            "TitForTat", "RandomStrategy", "AlwaysCooperate", "AlwaysDefect",
            "GrimTrigger", "TitForTwoTats", "Pavlov", "RandomCooperate",
            "Alternator", "SoftMajority", "HardMajority", "SuspiciousTitForTat",
            "TwoTitsForTat", "Prober", "ForgivingTitForTat", "Adaptive",
            "Spiteful", "GenerousTitForTat", "TitForTatWithNoise",
            "WinStayLoseShift", "TitForTatWithMemory", "Detective",
            "TitForTatWithDelay", "ContriteTitForTat"
        ]
        
        for strat in self.all_strats:
            self.strat_listbox.insert(tk.END, strat)
            
        # Select first 4 by default to keep previous behavior
        self.strat_listbox.selection_set(0)
        self.strat_listbox.selection_set(1)
        self.strat_listbox.selection_set(2)
        self.strat_listbox.selection_set(3)
        
        self.strat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=0, column=6, rowspan=3, padx=20, pady=5)

        self.btn_start = ttk.Button(btn_frame, text="Start Tournament", command=self.start_sim)
        self.btn_start.pack(fill=tk.X, pady=2)

        self.btn_stop = ttk.Button(btn_frame, text="Stop Tournament", command=self.stop_sim, state=tk.DISABLED)
        self.btn_stop.pack(fill=tk.X, pady=2)

        self.btn_export = ttk.Button(btn_frame, text="Export CSV", command=self.export_csv)
        self.btn_export.pack(fill=tk.X, pady=2)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = (
            "MatchID", "Round", "P1", "P1_Action", "P1_Payoff", "P1_Points",
            "P2", "P2_Action", "P2_Payoff", "P2_Points"
        )
        
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80, anchor=tk.CENTER)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_y.set)
        
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscroll=scrollbar_x.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

    def start_sim(self):
        try:
            n_agents = self.agents_var.get()
            n_matches = self.matches_var.get()
            rnds = self.rounds_var.get()
            t = self.t_var.get()
            r = self.r_var.get()
            p = self.p_var.get()
            s = self.s_var.get()
        except tk.TclError:
            messagebox.showerror("Error", "Please enter valid integers.")
            return

        selected_indices = self.strat_listbox.curselection()
        strats = [self.strat_listbox.get(i) for i in selected_indices]

        if not strats:
            messagebox.showerror("Error", "Select at least one strategy for the pool.")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        self.controller.start_tournament(n_agents, n_matches, rnds, t, r, p, s, strats)

    def stop_sim(self):
        self.controller.stop_tournament()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def on_match_update(self, entry):
        self.update_queue.put(entry)

    def on_simulation_complete(self):
        self.update_queue.put("SIM_COMPLETE")

    def process_queue(self):
        try:
            while True:
                item = self.update_queue.get_nowait()
                if item == "SIM_COMPLETE":
                    self.btn_start.config(state=tk.NORMAL)
                    self.btn_stop.config(state=tk.DISABLED)
                    messagebox.showinfo("Tournament", "Tournament Execution Finished.")
                else:
                    values = (
                        item["MatchID"], item["Round"],
                        item["P1"], item["Player1_Action"], item["Player1_Payoff"], item["Player1_ActualPoints"],
                        item["P2"], item["Player2_Action"], item["Player2_Payoff"], item["Player2_ActualPoints"]
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
                writer.writerow(["MatchID", "Round", "P1", "P1_Action", "P1_Payoff", "P1_Points", "P2", "P2_Action", "P2_Payoff", "P2_Points"])
                for res in results:
                    writer.writerow([res["MatchID"], res["Round"], res["P1"], res["Player1_Action"], res["Player1_Payoff"], res["Player1_ActualPoints"], res["P2"], res["Player2_Action"], res["Player2_Payoff"], res["Player2_ActualPoints"]])
            messagebox.showinfo("Export", f"Exported to {file_path}")

    def destroy_tab(self):
        self.controller.stop_tournament()
