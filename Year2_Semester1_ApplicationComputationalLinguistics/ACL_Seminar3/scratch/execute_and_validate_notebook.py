"""Executes all cells in ACL_Seminar_3_Zipf_Analysis.ipynb using nbclient from a clean kernel,
capturing all stdout, tables, and inline matplotlib plots directly into the notebook.
"""

import sys
from pathlib import Path
import nbformat
from nbclient import NotebookClient

notebook_path = Path("notebooks/ACL_Seminar_3_Zipf_Analysis.ipynb")
print(f"Loading notebook: {notebook_path.resolve()}")
nb = nbformat.read(notebook_path, as_version=4)

client = NotebookClient(
    nb,
    timeout=600,
    kernel_name="python3",
    allow_errors=False,  # fail immediately on any cell error
    record_timing=True,
)

print("Executing all cells from a clean kernel...")
try:
    client.execute()
    print("All cells executed successfully!")
except Exception as e:
    print(f"Error executing notebook: {e}", file=sys.stderr)
    raise

# Save executed notebook with all outputs and figures
with open(notebook_path, "w", encoding="utf-8") as f:
    nbformat.write(nb, f)

print(f"Saved executed notebook to {notebook_path.resolve()}")

