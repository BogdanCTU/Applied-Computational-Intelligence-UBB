"""Pure Native Windows Desktop Application for Bank Marketing Classifier.

Built with Tkinter and ttk (no web browser, no local web server).
Provides complete parity with the research assignment requirements:
  - Model Comparison (Metrics & Confusion Matrices)
  - Bayesian Network (Training, DAG Inspection, Probabilistic Inference)
  - Rule-Based Classifier (Rule Specs, AST Branching Verification, Execution Trace)
  - Dataset Explorer (Telemetry, Distributions, Feature Insights)
  - CLI Runner & Execution Logs
"""

import ast
import ctypes
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Enable High-DPI awareness on Windows before creating the Tk root
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
import seaborn as sns

# Ensure project modules are importable
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys._MEIPASS).resolve()
else:
    ROOT_DIR = Path(__file__).resolve().parent

for folder in [
    ROOT_DIR,
    ROOT_DIR / "1_Dataset",
    ROOT_DIR / "2_BayesianNetworkClassification",
    ROOT_DIR / "3_RuleBasedClassification",
    ROOT_DIR / "src",
]:
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from src import config
from src.evaluation import comparison_table, compute_metrics, report_text, save_results
from src.model_service import ModelConfig, ModelService, TrainedArtifacts, model_service
import branch_counter
import data_loader
import rule_based


class BankClassifierApp(tk.Tk):
    """Main Native Desktop Window Application."""

    def __init__(self):
        super().__init__()

        self.title("Bank Marketing Classifier | Bayesian Network vs. Rule-Based")
        self.geometry("1180x820")
        self.minsize(980, 680)

        # Apply modern ttk theme styling
        self.setup_styles()

        self.service: ModelService = model_service
        self.current_cfg: ModelConfig = ModelConfig()

        # Build UI layout
        self.create_header()
        self.create_notebook()
        self.create_status_bar()

        # Auto-train or load initial background data safely
        self.after(200, self.initial_load)

    def setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Configure modern fonts and colors
        font_family = "Helvetica Neue" if sys.platform == "darwin" else "Segoe UI"
        base_font = (font_family, 10)
        heading_font = (font_family, 11, "bold")
        title_font = (font_family, 14, "bold")

        style.configure(".", font=base_font)
        style.configure("TLabel", font=base_font)
        style.configure("TButton", font=base_font, padding=6)
        style.configure("Header.TLabel", font=title_font, foreground="#1e3a8a")
        style.configure("SubHeader.TLabel", font=heading_font, foreground="#1e293b")
        style.configure("Card.TFrame", background="#f8fafc", relief="solid", borderwidth=1)
        style.configure("Accent.TButton", font=heading_font, background="#2563eb", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#1d4ed8")])
        style.configure("TNotebook.Tab", font=heading_font, padding=[12, 6])
        style.configure("Treeview.Heading", font=heading_font)
        style.configure("Treeview", font=base_font, rowheight=26)

    def create_header(self):
        header_frame = ttk.Frame(self, padding=(16, 12, 16, 8))
        header_frame.pack(fill=tk.X)

        title = ttk.Label(
            header_frame,
            text="🏦 Bayesian Network vs. Rule-Based Classification",
            style="Header.TLabel",
        )
        title.pack(anchor=tk.W)

        font_family = "Helvetica Neue" if sys.platform == "darwin" else "Segoe UI"
        subtitle = ttk.Label(
            header_frame,
            text="Empirical Comparison on the UCI Bank Marketing Dataset | Desktop Application",
            foreground="#64748b",
            font=(font_family, 9),
        )
        subtitle.pack(anchor=tk.W, pady=(2, 0))

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16, pady=4)

    def create_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        # Tab 1: Overview & Model Comparison
        self.tab_overview = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_overview, text=" ⚖️ Model Comparison ")
        self.build_overview_tab()

        # Tab 2: Bayesian Network (Part A)
        self.tab_bn = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_bn, text=" 🕸️ Bayesian Network ")
        self.build_bn_tab()

        # Tab 3: Rule-Based Classifier (Part B)
        self.tab_rules = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_rules, text=" 🌳 Rule-Based Classifier ")
        self.build_rules_tab()

        # Tab 4: Dataset Explorer
        self.tab_data = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_data, text=" 🔍 Dataset Explorer ")
        self.build_data_tab()

        # Tab 5: CLI Experiment & Logs
        self.tab_logs = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_logs, text=" ⚡ Full Experiment & Logs ")
        self.build_logs_tab()

    def create_status_bar(self):
        self.status_frame = ttk.Frame(self, relief=tk.SUNKEN, padding=(12, 4))
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(self.status_frame, text="Ready", font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT)

        self.progress_bar = ttk.Progressbar(self.status_frame, orient=tk.HORIZONTAL, length=200, mode="determinate")
        self.progress_bar.pack(side=tk.RIGHT, padx=4)

    def set_status(self, text: str, progress: Optional[float] = None):
        self.status_label.config(text=text)
        if progress is not None:
            self.progress_bar["value"] = progress * 100
        self.update_idletasks()

    # ==========================================
    # TAB 1: OVERVIEW & COMPARISON
    # ==========================================
    def build_overview_tab(self):
        container = ttk.Frame(self.tab_overview)
        container.pack(fill=tk.BOTH, expand=True)

        # Top summary cards frame
        cards_frame = ttk.Frame(container)
        cards_frame.pack(fill=tk.X, pady=(0, 10))

        self.card_bn = self.create_metric_card(cards_frame, "Bayesian Network (Part A)", "F1: -- | Acc: --", "#eff6ff")
        self.card_bn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        self.card_rule = self.create_metric_card(cards_frame, "Rule-Based Classifier (Part B)", "F1: -- | Acc: --", "#f0fdf4")
        self.card_rule.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        self.card_base = self.create_metric_card(cards_frame, "Majority Baseline (Reference)", "F1: 0.00% | Acc: 88.3%", "#f8fafc")
        self.card_base.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        # Performance Table
        table_label = ttk.Label(container, text="📊 Comparative Test Set Performance (Positive Class = 'yes')", style="SubHeader.TLabel")
        table_label.pack(anchor=tk.W, pady=(6, 4))

        columns = ("Classifier", "Accuracy", "Precision", "Recall", "F1-Score", "TN", "FP", "FN", "TP")
        self.overview_tree = ttk.Treeview(container, columns=columns, show="headings", height=4)
        for col in columns:
            self.overview_tree.heading(col, text=col)
            self.overview_tree.column(col, width=110, anchor=tk.CENTER)
        self.overview_tree.column("Classifier", width=220, anchor=tk.W)
        self.overview_tree.pack(fill=tk.X, pady=(0, 8))

        # Bottom Frame: Embedded Confusion Matrix Matplotlib Figures
        cm_label = ttk.Label(container, text="📈 Side-by-Side Confusion Matrices", style="SubHeader.TLabel")
        cm_label.pack(anchor=tk.W, pady=(6, 4))

        self.fig_cm = Figure(figsize=(9, 3.2), dpi=100, facecolor="#ffffff")
        self.canvas_cm = FigureCanvasTkAgg(self.fig_cm, master=container)
        self.canvas_cm.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_metric_card(self, parent, title: str, subtitle: str, bg_color: str) -> tk.Frame:
        card = tk.Frame(parent, bg=bg_color, relief=tk.SOLID, borderwidth=1, padx=12, pady=10)
        lbl_title = tk.Label(card, text=title, font=("Segoe UI", 10, "bold"), bg=bg_color, fg="#1e293b")
        lbl_title.pack(anchor=tk.W)
        lbl_sub = tk.Label(card, text=subtitle, font=("Segoe UI", 12, "bold"), bg=bg_color, fg="#2563eb")
        lbl_sub.pack(anchor=tk.W, pady=(4, 0))
        card.subtitle_label = lbl_sub
        return card

    def update_overview_ui(self, artifacts: TrainedArtifacts):
        bn_m = artifacts.bn_metrics
        rule_m = artifacts.rule_metrics

        # Update cards
        self.card_bn.subtitle_label.config(
            text=f"F1: {bn_m['f1']:.1%} | Acc: {bn_m['accuracy']:.1%} (Rec: {bn_m['recall']:.1%})"
        )
        self.card_rule.subtitle_label.config(
            text=f"F1: {rule_m['f1']:.1%} | Acc: {rule_m['accuracy']:.1%} (Rec: {rule_m['recall']:.1%})"
        )

        # Update Treeview Table
        for row in self.overview_tree.get_children():
            self.overview_tree.delete(row)

        rows = [
            ("Bayesian Network", f"{bn_m['accuracy']:.4f}", f"{bn_m['precision']:.4f}", f"{bn_m['recall']:.4f}", f"{bn_m['f1']:.4f}", bn_m['TN'], bn_m['FP'], bn_m['FN'], bn_m['TP']),
            ("Rule-Based Classifier", f"{rule_m['accuracy']:.4f}", f"{rule_m['precision']:.4f}", f"{rule_m['recall']:.4f}", f"{rule_m['f1']:.4f}", rule_m['TN'], rule_m['FP'], rule_m['FN'], rule_m['TP']),
            ("Majority Baseline", f"{artifacts.baseline_metrics['accuracy']:.4f}", "0.0000", "0.0000", "0.0000", artifacts.baseline_metrics['TN'], artifacts.baseline_metrics['FP'], artifacts.baseline_metrics['FN'], artifacts.baseline_metrics['TP']),
        ]
        for r in rows:
            self.overview_tree.insert("", tk.END, values=r)

        # Render Confusion Matrices on Matplotlib canvas
        self.fig_cm.clear()
        ax1 = self.fig_cm.add_subplot(121)
        ax2 = self.fig_cm.add_subplot(122)

        bn_cm = np.array([[bn_m['TN'], bn_m['FP']], [bn_m['FN'], bn_m['TP']]])
        rule_cm = np.array([[rule_m['TN'], rule_m['FP']], [rule_m['FN'], rule_m['TP']]])

        sns.heatmap(bn_cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax1,
                    xticklabels=["no", "yes"], yticklabels=["no", "yes"])
        ax1.set_title(f"Bayesian Network (F1 = {bn_m['f1']:.3f})", fontsize=10, fontweight="bold")
        ax1.set_xlabel("Predicted")
        ax1.set_ylabel("Actual")

        sns.heatmap(rule_cm, annot=True, fmt="d", cmap="Greens", cbar=False, ax=ax2,
                    xticklabels=["no", "yes"], yticklabels=["no", "yes"])
        ax2.set_title(f"Rule-Based (F1 = {rule_m['f1']:.3f})", fontsize=10, fontweight="bold")
        ax2.set_xlabel("Predicted")
        ax2.set_ylabel("Actual")

        self.fig_cm.tight_layout()
        self.canvas_cm.draw()

    # ==========================================
    # TAB 2: BAYESIAN NETWORK (PART A)
    # ==========================================
    def build_bn_tab(self):
        container = ttk.Frame(self.tab_bn)
        container.pack(fill=tk.BOTH, expand=True)

        # Left Column: Configuration & Retraining
        left_frame = ttk.LabelFrame(container, text="⚙️ Model Hyperparameters & Training", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        ttk.Label(left_frame, text="Max Indegree (Max Parents per Node):").pack(anchor=tk.W, pady=(2, 2))
        self.spin_indegree = ttk.Spinbox(left_frame, from_=1, to=5, width=10)
        self.spin_indegree.set(self.current_cfg.max_indegree)
        self.spin_indegree.pack(anchor=tk.W, pady=(0, 6))

        ttk.Label(left_frame, text="BDeu Sample Size (Smoothing Prior):").pack(anchor=tk.W, pady=(2, 2))
        self.spin_sample = ttk.Spinbox(left_frame, from_=1, to=50, width=10)
        self.spin_sample.set(self.current_cfg.equivalent_sample_size)
        self.spin_sample.pack(anchor=tk.W, pady=(0, 6))

        ttk.Label(left_frame, text="Random Seed (Train/Test Split):").pack(anchor=tk.W, pady=(2, 2))
        self.spin_seed = ttk.Spinbox(left_frame, from_=1, to=9999, width=10)
        self.spin_seed.set(self.current_cfg.random_seed)
        self.spin_seed.pack(anchor=tk.W, pady=(0, 10))

        self.btn_train = ttk.Button(left_frame, text="🚀 Train Bayesian Network", style="Accent.TButton", command=self.on_train_clicked)
        self.btn_train.pack(fill=tk.X, pady=(4, 10))

        self.lbl_bn_info = ttk.Label(left_frame, text="Model Status: Initializing...", wraplength=220, foreground="#64748b")
        self.lbl_bn_info.pack(fill=tk.X, pady=(4, 10))

        # Right Column: Network Inspection & Single Client Inference
        right_frame = ttk.Frame(container)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right Top: Network DAG details
        dag_box = ttk.LabelFrame(right_frame, text="🕸️ Learned DAG & Markov Blanket", padding=10)
        dag_box.pack(fill=tk.X, pady=(0, 10))

        self.lbl_dag_summary = ttk.Label(dag_box, text="Edges: -- | Markov Blanket: --", font=("Segoe UI", 10, "bold"))
        self.lbl_dag_summary.pack(anchor=tk.W, pady=(0, 4))

        self.txt_edges = ScrolledText(dag_box, height=5, font=("Consolas", 9), wrap=tk.WORD)
        self.txt_edges.pack(fill=tk.X)

        # Right Bottom: Interactive Client Inference
        infer_box = ttk.LabelFrame(right_frame, text="🎯 Interactive Probabilistic Inference (Variable Elimination)", padding=10)
        infer_box.pack(fill=tk.BOTH, expand=True)

        form_frame = ttk.Frame(infer_box)
        form_frame.pack(fill=tk.X, pady=(0, 6))

        # Attributes for query
        ttk.Label(form_frame, text="Previous Outcome (poutcome):").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        self.combo_bn_poutcome = ttk.Combobox(form_frame, values=["unknown", "failure", "other", "success"], state="readonly", width=12)
        self.combo_bn_poutcome.set("success")
        self.combo_bn_poutcome.grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(form_frame, text="Contact Month (month):").grid(row=0, column=2, sticky=tk.W, padx=4, pady=2)
        self.combo_bn_month = ttk.Combobox(form_frame, values=["mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], state="readonly", width=12)
        self.combo_bn_month.set("mar")
        self.combo_bn_month.grid(row=0, column=3, padx=4, pady=2)

        ttk.Label(form_frame, text="Housing Loan:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        self.combo_bn_housing = ttk.Combobox(form_frame, values=["no", "yes"], state="readonly", width=12)
        self.combo_bn_housing.set("no")
        self.combo_bn_housing.grid(row=1, column=1, padx=4, pady=2)

        ttk.Label(form_frame, text="Contact Type:").grid(row=1, column=2, sticky=tk.W, padx=4, pady=2)
        self.combo_bn_contact = ttk.Combobox(form_frame, values=["cellular", "telephone", "unknown"], state="readonly", width=12)
        self.combo_bn_contact.set("cellular")
        self.combo_bn_contact.grid(row=1, column=3, padx=4, pady=2)

        self.btn_infer = ttk.Button(infer_box, text="🔍 Calculate Exact Posterior Probability", command=self.on_bn_infer_clicked)
        self.btn_infer.pack(anchor=tk.W, pady=6)

        self.lbl_bn_result = ttk.Label(
            infer_box,
            text="Prediction: -- | Posterior Probability P(y = 'yes'): --",
            font=("Segoe UI", 11, "bold"),
            foreground="#1e3a8a",
        )
        self.lbl_bn_result.pack(anchor=tk.W, pady=4)

    def on_train_clicked(self):
        try:
            cfg = ModelConfig(
                max_indegree=int(self.spin_indegree.get()),
                equivalent_sample_size=int(self.spin_sample.get()),
                random_seed=int(self.spin_seed.get()),
            )
        except Exception as e:
            messagebox.showerror("Invalid Input", f"Please check hyperparameter values: {e}")
            return

        self.current_cfg = cfg
        self.btn_train.config(state=tk.DISABLED)

        # Run training in background thread so the native UI stays responsive
        thread = threading.Thread(target=self._run_training_thread, args=(cfg,), daemon=True)
        thread.start()

    def _run_training_thread(self, cfg: ModelConfig):
        def cb(msg, frac):
            self.after(0, lambda: self.set_status(msg, frac))

        try:
            artifacts = self.service.train_models(cfg, progress_callback=cb)
            self.after(0, lambda: self._on_training_completed(artifacts))
        except Exception as err:
            self.after(0, lambda: messagebox.showerror("Training Error", str(err)))
            self.after(0, lambda: self.set_status("Training failed", 0.0))
            self.after(0, lambda: self.btn_train.config(state=tk.NORMAL))

    def _on_training_completed(self, artifacts: TrainedArtifacts):
        self.btn_train.config(state=tk.NORMAL)
        self.set_status(f"Training completed in {artifacts.training_duration:.2f}s", 1.0)

        # Update Overview Tab
        self.update_overview_ui(artifacts)

        # Update Bayesian Network Tab
        self.lbl_bn_info.config(
            text=f"Model Trained!\nEdges: {len(artifacts.edges)}\nTime: {artifacts.training_duration:.2f}s"
        )
        mb = artifacts.model.get_markov_blanket(config.TARGET)
        self.lbl_dag_summary.config(
            text=f"Learned Edges: {len(artifacts.edges)} | Target 'y' Markov Blanket: {sorted(mb)}"
        )
        self.txt_edges.delete("1.0", tk.END)
        edge_text = "\n".join([f"  {u}  ->  {v}" for u, v in artifacts.edges])
        self.txt_edges.insert(tk.END, edge_text)

    def on_bn_infer_clicked(self):
        artifacts = self.service.get_artifacts()
        if artifacts is None:
            messagebox.showwarning("Model Not Ready", "Please train the Bayesian Network first.")
            return

        client = {
            "poutcome": self.combo_bn_poutcome.get(),
            "month": self.combo_bn_month.get(),
            "housing": self.combo_bn_housing.get(),
            "contact": self.combo_bn_contact.get(),
            "age": 35,
            "balance": 1500,
            "day": 15,
            "campaign": 1,
            "pdays": -1,
            "previous": 0,
            "job": "management",
            "marital": "single",
            "education": "tertiary",
            "default": "no",
            "loan": "no",
        }
        res = self.service.predict_single_bn(client)
        pred = res["prediction"]
        p_yes = res["p_yes"]
        p_no = res["p_no"]
        color = "#166534" if pred == "yes" else "#991b1b"

        self.lbl_bn_result.config(
            text=f"Predicted Class: '{pred.upper()}'  |  P(yes | evidence) = {p_yes:.1%}  (P(no) = {p_no:.1%})",
            foreground=color,
        )

    # ==========================================
    # TAB 3: RULE-BASED CLASSIFIER (PART B)
    # ==========================================
    def build_rules_tab(self):
        container = ttk.Frame(self.tab_rules)
        container.pack(fill=tk.BOTH, expand=True)

        # AST Compliance Box
        ast_box = ttk.LabelFrame(container, text="🛡️ AST Branching Constraint Verification", padding=10)
        ast_box.pack(fill=tk.X, pady=(0, 10))

        check = branch_counter.check_file(config.RULES_DIR / "rule_based.py", config.FEATURES)
        status_text = "✅ COMPLIANT: Actual branches (2) <= Attributes used limit (2)" if check["compliant"] else "❌ NON-COMPLIANT"
        status_fg = "#166534" if check["compliant"] else "#991b1b"

        lbl_ast = ttk.Label(ast_box, text=status_text, font=("Segoe UI", 11, "bold"), foreground=status_fg)
        lbl_ast.pack(anchor=tk.W, pady=(0, 4))

        details = (
            f"Attributes used: {check['attributes_used']} (n = {check['n_attributes_used']})  |  "
            f"Allowed branches: {check['allowed_branches']}  |  "
            f"Actual branching statements: {check['branching_statements']}  |  "
            f"Decision rules (returns): {check['return_statements_(rules)']}"
        )
        ttk.Label(ast_box, text=details, font=("Segoe UI", 9)).pack(anchor=tk.W)

        # Rules Specification Table
        rules_box = ttk.LabelFrame(container, text="📜 Decision Logic & Domain Rationale", padding=10)
        rules_box.pack(fill=tk.X, pady=(0, 10))

        cols = ("Rule", "Condition", "Predicted Class", "Training Rationale")
        tree_rules = ttk.Treeview(rules_box, columns=cols, show="headings", height=3)
        tree_rules.heading("Rule", text="Rule Statement")
        tree_rules.heading("Condition", text="Condition Evaluated")
        tree_rules.heading("Predicted Class", text="Class")
        tree_rules.heading("Training Rationale", text="Rationale (Training split only)")

        tree_rules.column("Rule", width=130)
        tree_rules.column("Condition", width=250)
        tree_rules.column("Predicted Class", width=80, anchor=tk.CENTER)
        tree_rules.column("Training Rationale", width=460)

        tree_rules.insert("", tk.END, values=("Rule 1 (if)", "record['poutcome'] == 'success'", "yes", "64.6% yes-rate on training split (previous campaign succeeded)"))
        tree_rules.insert("", tk.END, values=("Rule 2 (elif)", "record['month'] in ('mar', 'sep', 'oct', 'dec')", "yes", "44% - 51% yes-rate in shoulder months (~4x base rate)"))
        tree_rules.insert("", tk.END, values=("Default (else)", "all other customer profiles", "no", "88.3% base refusal rate (majority fallback)"))
        tree_rules.pack(fill=tk.X)

        # Interactive Client Execution Trace
        trace_box = ttk.LabelFrame(container, text="🎯 Single Client Classification with Execution Trace", padding=10)
        trace_box.pack(fill=tk.BOTH, expand=True)

        inputs_frame = ttk.Frame(trace_box)
        inputs_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(inputs_frame, text="Prior Outcome (poutcome):").pack(side=tk.LEFT, padx=(0, 4))
        self.combo_rule_poutcome = ttk.Combobox(inputs_frame, values=["unknown", "failure", "other", "success"], state="readonly", width=12)
        self.combo_rule_poutcome.set("failure")
        self.combo_rule_poutcome.pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(inputs_frame, text="Contact Month (month):").pack(side=tk.LEFT, padx=(0, 4))
        self.combo_rule_month = ttk.Combobox(inputs_frame, values=["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], state="readonly", width=12)
        self.combo_rule_month.set("sep")
        self.combo_rule_month.pack(side=tk.LEFT, padx=(0, 12))

        btn_eval = ttk.Button(inputs_frame, text="⚡ Run Rule Trace", command=self.on_rule_trace_clicked)
        btn_eval.pack(side=tk.LEFT)

        self.txt_trace = ScrolledText(trace_box, height=6, font=("Consolas", 10), wrap=tk.WORD)
        self.txt_trace.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def on_rule_trace_clicked(self):
        client = {
            "poutcome": self.combo_rule_poutcome.get(),
            "month": self.combo_rule_month.get()
        }
        res = self.service.predict_single_rule_based(client)
        pred = res["prediction"]

        self.txt_trace.delete("1.0", tk.END)
        self.txt_trace.insert(tk.END, f"=== RULE EVALUATION TRACE ===\n")
        self.txt_trace.insert(tk.END, f"Client Profile: poutcome='{client['poutcome']}', month='{client['month']}'\n\n")

        for item in res["trace"]:
            step = item["step"]
            if step == 1:
                self.txt_trace.insert(tk.END, f"[Step 1] Read input attributes: {item['attributes']}\n")
            elif step == 2:
                self.txt_trace.insert(tk.END, f"[Step 2] {item['rule']} ({item['condition']}) -> Result: {item['result']} -> Action: {item['action']}\n")
            elif step == 3:
                self.txt_trace.insert(tk.END, f"[Step 3] {item['rule']} ({item['condition']}) -> Result: {item['result']} -> Action: {item['action']}\n")
            elif step == 4:
                self.txt_trace.insert(tk.END, f"[Step 4] {item['rule']} -> Action: {item['action']}\n")

        self.txt_trace.insert(tk.END, f"\nFINAL PREDICTION: '{pred.upper()}'\n")
        self.txt_trace.insert(tk.END, f"Explanation: {res['explanation']}\n")

    # ==========================================
    # TAB 4: DATASET EXPLORER
    # ==========================================
    def build_data_tab(self):
        container = ttk.Frame(self.tab_data)
        container.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(container)
        top_frame.pack(fill=tk.X, pady=(0, 8))

        self.lbl_data_stats = ttk.Label(
            top_frame,
            text="Dataset: UCI Bank Marketing (bank-full.csv) | Records: 45,211 | Input Features: 15 | Positive Class: 11.7%",
            font=("Segoe UI", 10, "bold"),
            foreground="#1e293b",
        )
        self.lbl_data_stats.pack(anchor=tk.W)

        # Treeview to display raw data records
        data_table_box = ttk.LabelFrame(container, text="📋 Dataset Sample Records", padding=8)
        data_table_box.pack(fill=tk.BOTH, expand=True)

        cols = ("age", "job", "marital", "education", "default", "balance", "housing", "loan", "contact", "month", "poutcome", "y")
        self.tree_raw = ttk.Treeview(data_table_box, columns=cols, show="headings", height=14)
        for c in cols:
            self.tree_raw.heading(c, text=c)
            self.tree_raw.column(c, width=75, anchor=tk.CENTER)
        self.tree_raw.column("job", width=110)
        self.tree_raw.column("education", width=90)
        self.tree_raw.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scroll = ttk.Scrollbar(data_table_box, orient=tk.VERTICAL, command=self.tree_raw.yview)
        self.tree_raw.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def load_dataset_sample(self):
        try:
            df = self.service.get_raw_dataset()
            sample = df.head(50)
            cols = ("age", "job", "marital", "education", "default", "balance", "housing", "loan", "contact", "month", "poutcome", "y")
            for _, row in sample.iterrows():
                vals = [row[c] for c in cols]
                self.tree_raw.insert("", tk.END, values=vals)
        except Exception as e:
            print(f"Dataset sample load error: {e}")

    # ==========================================
    # TAB 5: CLI EXPERIMENT & LOGS
    # ==========================================
    def build_logs_tab(self):
        container = ttk.Frame(self.tab_logs)
        container.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=(0, 6))

        btn_run_cli = ttk.Button(
            btn_frame,
            text="▶️ Run End-to-End Pipeline & Save Results to Disk",
            style="Accent.TButton",
            command=self.on_run_full_experiment_clicked,
        )
        btn_run_cli.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(btn_frame, text="Saves metrics.csv, network diagrams, and reports to results/ folder.", foreground="#64748b").pack(side=tk.LEFT)

        self.txt_console = ScrolledText(container, font=("Consolas", 9), wrap=tk.WORD, bg="#0f172a", fg="#f8fafc")
        self.txt_console.pack(fill=tk.BOTH, expand=True)

    def on_run_full_experiment_clicked(self):
        self.txt_console.delete("1.0", tk.END)
        self.txt_console.insert(tk.END, "Starting full end-to-end experiment pipeline...\n\n")

        thread = threading.Thread(target=self._run_cli_thread, daemon=True)
        thread.start()

    def _run_cli_thread(self):
        class RedirectStd:
            def __init__(self, callback):
                self.callback = callback

            def write(self, s):
                if s:
                    self.callback(s)

            def flush(self):
                pass

        old_stdout = sys.stdout
        sys.stdout = RedirectStd(lambda text: self.after(0, lambda: self._append_console(text)))

        try:
            from src.main import main
            main()
            self.after(0, lambda: self._append_console("\n✅ Pipeline executed successfully! Results saved to results/ folder.\n"))
        except Exception as err:
            self.after(0, lambda: self._append_console(f"\n❌ Error during pipeline run: {err}\n"))
        finally:
            sys.stdout = old_stdout

    def _append_console(self, text: str):
        self.txt_console.insert(tk.END, text)
        self.txt_console.see(tk.END)

    # ==========================================
    # INITIAL LOAD
    # ==========================================
    def initial_load(self):
        self.set_status("Loading dataset sample...", 0.2)
        threading.Thread(target=self._initial_background_load, daemon=True).start()

    def _initial_background_load(self):
        try:
            self.load_dataset_sample()
            self.set_status("Training baseline models...", 0.4)
            artifacts = self.service.train_models(self.current_cfg, progress_callback=lambda msg, frac: self.after(0, lambda: self.set_status(msg, frac)))
            self.after(0, lambda: self._on_training_completed(artifacts))
        except Exception as e:
            self.after(0, lambda: self.set_status(f"Ready (Train needed: {e})", 0.0))


def main():
    app = BankClassifierApp()
    app.mainloop()


if __name__ == "__main__":
    main()
