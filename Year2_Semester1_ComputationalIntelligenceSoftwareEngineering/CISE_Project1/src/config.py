"""Central configuration: paths, random seed and the explicit feature selection.

Keeping these values in one place guarantees that the Bayesian Network and the
rule-based classifier are always run with exactly the same settings.
"""

import sys
from pathlib import Path

# --- Paths
if getattr(sys, "frozen", False):
    # Running inside a PyInstaller bundle
    BUNDLE_ROOT = Path(sys._MEIPASS).resolve()
    EXE_ROOT = Path(sys.executable).resolve().parent
    PROJECT_ROOT = BUNDLE_ROOT

    # Priority for DATA_DIR:
    # 1. External dataset next to the .exe
    # 2. Bundled dataset inside the bundle
    # 3. Fallback to external path so auto-download creates it next to .exe
    if (EXE_ROOT / "1_Dataset" / "bank-full.csv").exists():
        DATA_DIR = EXE_ROOT / "1_Dataset"
    elif (BUNDLE_ROOT / "1_Dataset" / "bank-full.csv").exists():
        DATA_DIR = BUNDLE_ROOT / "1_Dataset"
    else:
        DATA_DIR = EXE_ROOT / "1_Dataset"

    BN_DIR = BUNDLE_ROOT / "2_BayesianNetworkClassification"
    RULES_DIR = BUNDLE_ROOT / "3_RuleBasedClassification"
    RESULTS_DIR = EXE_ROOT / "results"
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    DATA_DIR = PROJECT_ROOT / "1_Dataset"                       # dataset + data_loader.py
    BN_DIR = PROJECT_ROOT / "2_BayesianNetworkClassification"   # Part A code
    RULES_DIR = PROJECT_ROOT / "3_RuleBasedClassification"      # Part B code
    RESULTS_DIR = PROJECT_ROOT / "results"

# Folder names that start with a digit cannot be imported as Python packages, so we
# add the three part-folders to the import path. Their modules (data_loader,
# bayesian_network, rule_based) are then imported as ordinary top-level modules.
for _folder in (DATA_DIR, BN_DIR, RULES_DIR):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

# --- Dataset (official UCI source)
UCI_ZIP_URL = "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip"
UCI_PAGE_URL = "https://archive.ics.uci.edu/dataset/222/bank%2Bmarketing"
# The UCI zip contains two nested zips. We use "bank.zip" -> "bank-full.csv"
# (45,211 records, 16 input attributes + target, the "full" dataset).
CSV_NAME = "bank-full.csv"
CSV_PATH = DATA_DIR / CSV_NAME

# --- Experiment settings
RANDOM_SEED = 42
TEST_SIZE = 0.2

# --- Target
TARGET = "y"
POSITIVE_LABEL = "yes"   # subscribed to a term deposit  (the class we care about)
NEGATIVE_LABEL = "no"
LABELS = [NEGATIVE_LABEL, POSITIVE_LABEL]  # fixed order used by every metric

# --- Feature selection (used by BOTH classifiers)
# `duration` is deliberately excluded: it is the length of the *current* call,
# only known after the call ends (and the outcome is almost determined by it).
# Including it would be target leakage for a realistic "before calling" model.
EXCLUDED_FEATURES = ["duration"]

CATEGORICAL_FEATURES = [
    "job", "marital", "education", "default", "housing", "loan",
    "contact", "month", "poutcome",
]
NUMERIC_FEATURES = ["age", "balance", "day", "campaign", "pdays", "previous"]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES  # 15 input attributes

# Number of quantile bins used to discretise each numeric feature
# (pdays is handled separately, see preprocessing.py).
N_BINS = {"age": 4, "balance": 4, "day": 3, "campaign": 3, "previous": 3, "pdays": 3}

# --- Bayesian Network settings
MAX_INDEGREE = 3             # at most 3 parents per node (keeps CPTs small)
BDEU_EQUIVALENT_SAMPLE_SIZE = 5  # strength of the smoothing prior for the CPTs
