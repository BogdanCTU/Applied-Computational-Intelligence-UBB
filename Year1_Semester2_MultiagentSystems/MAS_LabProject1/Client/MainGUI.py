import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import queue
import csv
import sys
import os

# Add the parent directory and backend directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(parent_dir, "Backend")

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from SimulationController import SimulationController

class MainGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SPADE MAS Simulation - Prisoner's Dilemma")
        self.root.geometry("800x600")

        # Queue for thread-safe UI updates
        self.update_queue = queue.Queue()
        
        # Controller
        self.controller = SimulationController(
            update_callback=self.on_round_update,
            completion_callback=self.on_simulation_complete
        )

        self.setup_ui()
        
        # Poll the queue for updates
        self.root.after(100, self.process_queue)

    def setup_ui(self):
        # Top Frame - Controls
        control_frame = ttk.LabelFrame(self.root, text="Simulation Parameters")
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(control_frame, text="Rounds:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.rounds_var = tk.IntVar(value=100)
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

        # Strategy Selection
        ttk.Label(control_frame, text="P1 Strategy:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.p1_strat_var = tk.StringVar(value="TitForTat")
        ttk.Combobox(control_frame, textvariable=self.p1_strat_var, values=["TitForTat", "RandomStrategy", "AlwaysCooperate", "AlwaysDefect"], state="readonly", width=15).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(control_frame, text="P2 Strategy:").grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)
        self.p2_strat_var = tk.StringVar(value="RandomStrategy")
        ttk.Combobox(control_frame, textvariable=self.p2_strat_var, values=["TitForTat", "RandomStrategy", "AlwaysCooperate", "AlwaysDefect"], state="readonly", width=15).grid(row=2, column=3, padx=5, pady=5)

        # Buttons Frame
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=0, column=6, rowspan=3, padx=20, pady=5)

        self.btn_start = ttk.Button(btn_frame, text="Start Simulation", command=self.start_sim)
        self.btn_start.pack(fill=tk.X, pady=2)

        self.btn_stop = ttk.Button(btn_frame, text="Stop Simulation", command=self.stop_sim, state=tk.DISABLED)
        self.btn_stop.pack(fill=tk.X, pady=2)

        self.btn_export = ttk.Button(control_frame, text="Export CSV", command=self.export_csv)
        self.btn_export.grid(row=1, column=4, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # Middle Frame - Treeview
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = (
            "Round", "Player1_Action", "Player1_Payoff", "Player1_ActualPoints",
            "Player2_Action", "Player2_Payoff", "Player2_ActualPoints"
        )
        
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_y.set)
        
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscroll=scrollbar_x.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

    def start_sim(self):
        # Validate inputs
        try:
            rnds = self.rounds_var.get()
            t = self.t_var.get()
            r = self.r_var.get()
            p = self.p_var.get()
            s = self.s_var.get()
            p1_strat = self.p1_strat_var.get()
            p2_strat = self.p2_strat_var.get()
        except tk.TclError:
            messagebox.showerror("Error", "Please enter valid integers for parameters.")
            return

        if not (t > r > p > s):
            messagebox.showerror("Error", "Payoff conditions not met: must be T > R > P > S.")
            return

        if rnds <= 0:
            messagebox.showerror("Error", "Rounds must be positive.")
            return

        # Clear existing Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        # Start Controller
        self.controller.start_simulation(rnds, t, r, p, s, p1_strat, p2_strat)

    def stop_sim(self):
        self.controller.stop_simulation()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def on_round_update(self, result_entry):
        # Being called from the background asyncio/SPADE thread
        self.update_queue.put(result_entry)

    def on_simulation_complete(self):
        # To be thread-safe, put a special marker telling UI to update buttons
        self.update_queue.put("SIM_COMPLETE")

    def process_queue(self):
        try:
            # Process everything currently in the queue
            while True:
                item = self.update_queue.get_nowait()
                if item == "SIM_COMPLETE":
                    self.btn_start.config(state=tk.NORMAL)
                    self.btn_stop.config(state=tk.DISABLED)
                    messagebox.showinfo("Simulation", "Simulation Execution Finished.")
                else:
                    # It's a dictionary
                    values = (
                        item["Round"],
                        item["Player1_Action"],
                        item["Player1_Payoff"],
                        item["Player1_ActualPoints"],
                        item["Player2_Action"],
                        item["Player2_Payoff"],
                        item["Player2_ActualPoints"]
                    )
                    self.tree.insert("", tk.END, values=values)
                    # Scroll to bottom
                    self.tree.yview_moveto(1)
                
                self.update_queue.task_done()
        except queue.Empty:
            pass
            
        # Re-schedule polling
        self.root.after(100, self.process_queue)

    def export_csv(self):
        results = self.controller.get_results()
        if not results:
            messagebox.showinfo("Export", "No results to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Save Results As CSV"
        )
        if not file_path:
            return

        try:
            with open(file_path, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Round", "Player1_Action", "Player1_Payoff", "Player1_ActualPoints",
                    "Player2_Action", "Player2_Payoff", "Player2_ActualPoints"
                ])
                for res in results:
                    writer.writerow([
                        res["Round"], res["Player1_Action"], res["Player1_Payoff"], res["Player1_ActualPoints"],
                        res["Player2_Action"], res["Player2_Payoff"], res["Player2_ActualPoints"]
                    ])
            messagebox.showinfo("Export", f"Results successfully exported to\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to write file:\n{e}")

if __name__ == "__main__":
    app_root = tk.Tk()
    gui = MainGUI(app_root)
    app_root.protocol("WM_DELETE_WINDOW", lambda: (gui.controller.stop_simulation(), app_root.destroy()))
    app_root.mainloop()
