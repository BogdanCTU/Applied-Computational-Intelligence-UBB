"""Configuration module for Seminar 4 IR System (Part 1).

Defines project directory structure, dataset locations, constants,
and runtime settings.
"""

from pathlib import Path
import sys

# Directory Paths
SOLUTION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SOLUTION_DIR.parent

# Add paths to sys.path to enable clean imports across tests and scripts
for p in [str(SOLUTION_DIR), str(SOLUTION_DIR / "src"), str(PROJECT_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Data Directories
DATA_DIR = SOLUTION_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Fallback dataset directory in workspace
WORKSPACE_DATASET_DIR = PROJECT_ROOT / "2_Dataset" / "cacm"

# Input Files
RAW_CACM_FILE = RAW_DATA_DIR / "cacm.all"
RAW_QRELS_FILE = RAW_DATA_DIR / "qrels.text"
RAW_QUERY_FILE = RAW_DATA_DIR / "query.text"

# Fallback Input Files
FALLBACK_CACM_FILE = WORKSPACE_DATASET_DIR / "cacm.all"
FALLBACK_QRELS_FILE = WORKSPACE_DATASET_DIR / "qrels.text"
FALLBACK_QUERY_FILE = WORKSPACE_DATASET_DIR / "query.text"

# Processed Files
PROCESSED_DOCS_FILE = PROCESSED_DATA_DIR / "cacm_documents.json"
STOP_WORDS_FILE = PROCESSED_DATA_DIR / "stop_words.json"
RELEVANCE_JUDGMENTS_FILE = PROCESSED_DATA_DIR / "relevance_judgments.json"

# Output Directories & Files
OUTPUT_DIR = PROJECT_ROOT / "3_Output"
INVERTED_INDEX_FILE = OUTPUT_DIR / "inverted_index.json"
RESULTS_JSON_FILE = OUTPUT_DIR / "results.json"
TEST_RESULTS_CSV_FILE = OUTPUT_DIR / "test_results.csv"
PERFORMANCE_JSON_FILE = OUTPUT_DIR / "performance.json"

# Documentation Paths
DOCS_DIR = PROJECT_ROOT / "4_Documentation"
RESULTS_MD_FILE = DOCS_DIR / "results.md"
README_MD_FILE = DOCS_DIR / "README.md"
IMPLEMENTATION_MD_FILE = DOCS_DIR / "implementation.md"
SEMINAR_REPORT_PDF = DOCS_DIR / "seminar_report.pdf"

# Tests Directory
TESTS_DIR = PROJECT_ROOT / "2_Tests"

# Constants
NUM_STOP_WORDS = 7
DOC_ID_PREFIX = "CACM-"
# Zero padding: minimum width 3 characters (e.g. CACM-001, CACM-015, CACM-1410)
DOC_ID_PADDING = 3

# Test queries covering diverse document-frequency distributions
# database: low frequency (df=14)
# compiler: medium frequency (df=84)
# algorithm: high frequency (df=1194)
DEFAULT_TEST_QUERIES = ["database", "compiler", "algorithm"]

TOP_K_LIST = [3, 7]
STUDENT_NAME = "Popa Bogdan-Stefan"  # Identified student name from project path
