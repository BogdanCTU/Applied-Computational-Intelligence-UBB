"""Download, load and inspect the UCI Bank Marketing dataset."""

import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from src import config

MANUAL_INSTRUCTIONS = f"""
Automatic download failed. Please download the dataset manually:
  1. Open {config.UCI_PAGE_URL} and click "Download".
  2. Unzip the archive, then unzip the inner 'bank.zip'.
  3. Copy '{config.CSV_NAME}' to: {config.CSV_PATH}
Then run the program again.
"""


def download_dataset(csv_path: Path = config.CSV_PATH) -> Path:
    """Download the dataset from UCI (only if it is not already on disk)."""
    if csv_path.exists():
        return csv_path
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading dataset from {config.UCI_ZIP_URL} ...")
    try:
        with urllib.request.urlopen(config.UCI_ZIP_URL, timeout=60) as response:
            outer = zipfile.ZipFile(io.BytesIO(response.read()))
        # The outer zip contains 'bank.zip' (and 'bank-additional.zip').
        inner = zipfile.ZipFile(io.BytesIO(outer.read("bank.zip")))
        csv_path.write_bytes(inner.read(config.CSV_NAME))
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        raise RuntimeError(f"Could not download the dataset: {error}\n{MANUAL_INSTRUCTIONS}") from error
    print(f"Saved dataset to {csv_path}")
    return csv_path


def load_dataset(csv_path: Path = config.CSV_PATH) -> pd.DataFrame:
    """Load bank-full.csv (downloading it first if needed).

    Values are read as plain Python strings/ints so that later steps behave the same
    regardless of the pandas version.
    """
    download_dataset(csv_path)
    df = pd.read_csv(csv_path, sep=";", skipinitialspace=True)
    required = set(config.FEATURES) | {config.TARGET, "duration"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing expected columns: {sorted(missing)}")
    return df


def inspect_dataset(df: pd.DataFrame) -> str:
    """Return a human-readable report about the raw dataset (before preprocessing)."""
    lines: list[str] = []
    n_inputs = df.shape[1] - 1
    lines.append(f"Records: {len(df)}")
    lines.append(f"Columns: {df.shape[1]} ({n_inputs} input attributes + target '{config.TARGET}')")
    lines.append(f"Duplicate rows: {int(df.duplicated().sum())}")
    lines.append("")
    lines.append("Attributes, data types, missing values (NaN) and distinct values:")
    for col in df.columns:
        lines.append(f"  {col:<10} dtype={str(df[col].dtype):<8} NaN={int(df[col].isna().sum()):<3} "
                     f"distinct={df[col].nunique()}")
    lines.append("")
    lines.append("Categories spelled 'unknown' (the dataset's own missing-value marker):")
    for col in config.CATEGORICAL_FEATURES + [config.TARGET]:
        n_unknown = int((df[col] == "unknown").sum())
        if n_unknown:
            lines.append(f"  {col:<10} {n_unknown} ({n_unknown / len(df):.1%})")
    lines.append("")
    lines.append("Numeric attribute summary:")
    lines.append(df[config.NUMERIC_FEATURES + ["duration"]].describe().round(1).to_string())
    lines.append("")
    n_pdays = int((df["pdays"] == -1).sum())
    lines.append(f"Unusual values: pdays == -1 (client never previously contacted): "
                 f"{n_pdays} ({n_pdays / len(df):.1%}); negative balances: {int((df['balance'] < 0).sum())}")
    lines.append("")
    counts = df[config.TARGET].value_counts()
    lines.append("Target class distribution:")
    for label, n in counts.items():
        lines.append(f"  {label:<4} {n:>6} ({n / len(df):.1%})")
    return "\n".join(lines)
