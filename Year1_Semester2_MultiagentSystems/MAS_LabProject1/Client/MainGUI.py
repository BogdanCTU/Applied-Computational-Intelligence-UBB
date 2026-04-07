import tkinter as tk
from tkinter import ttk
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

from Tabs.TwoPlayerTab import TwoPlayerTab
from Tabs.HumanTab import HumanTab
from Tabs.TournamentTab import TournamentTab

class MainGUIContainer:
    def __init__(self, root):
        self.root = root
        self.root.title("SPADE MAS Simulation - Prisoner's Dilemma Suite")
        self.root.geometry("900x700")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_human = HumanTab(self.notebook, self.root)
        self.tab_two_player = TwoPlayerTab(self.notebook, self.root)
        self.tab_tournament = TournamentTab(self.notebook, self.root)

        self.notebook.add(self.tab_human, text="Player vs Human")
        self.notebook.add(self.tab_two_player, text="2 Players Simulation")
        self.notebook.add(self.tab_tournament, text="Multiple Agents Tournament")

    def destroy_all(self):
        self.tab_human.destroy_tab()
        self.tab_two_player.destroy_tab()
        self.tab_tournament.destroy_tab()

if __name__ == "__main__":
    # Add Tabs path temporarily to allow tab imports
    tabs_dir = os.path.join(current_dir, "Tabs")
    if tabs_dir not in sys.path:
        sys.path.insert(0, tabs_dir)

    app_root = tk.Tk()
    gui = MainGUIContainer(app_root)
    app_root.protocol("WM_DELETE_WINDOW", lambda: (gui.destroy_all(), app_root.destroy()))
    app_root.mainloop()
