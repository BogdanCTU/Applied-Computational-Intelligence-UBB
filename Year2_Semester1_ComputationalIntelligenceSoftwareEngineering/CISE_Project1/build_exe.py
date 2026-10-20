"""Automated build script for Windows executable.

Usage:
    python build_exe.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode/emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent


def build():
    print("=" * 70)
    print("BUILDING BANK MARKETING CLASSIFIER WINDOWS EXECUTABLE")
    print("=" * 70)
    print(f"Python Version: {sys.version}")
    print(f"Project Root:   {PROJECT_ROOT}")

    spec_file = PROJECT_ROOT / "BankMarketingClassifier.spec"
    if not spec_file.exists():
        print(f"Error: {spec_file} not found!")
        sys.exit(1)

    # Clean previous build directories if needed
    for folder_name in ["build", "dist", ".pyinstaller_cache"]:
        folder = PROJECT_ROOT / folder_name
        if folder.exists():
            print(f"Cleaning previous {folder_name}/ folder...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Warning: Could not fully remove {folder}: {e}")

    # Set local cache dir
    cache_dir = PROJECT_ROOT / ".pyinstaller_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["PYINSTALLER_CONFIG_DIR"] = str(cache_dir)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(spec_file),
    ]

    print("\nRunning PyInstaller command:")
    print(" ".join(cmd))
    print("\nCompiling... (this may take 1-3 minutes depending on disk speed)\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\n❌ Build failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    exe_path = PROJECT_ROOT / "dist" / "BankMarketingClassifier" / "BankMarketingClassifier.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 70)
        print("✅ BUILD SUCCEEDED!")
        print("=" * 70)
        print(f"Executable Location: {exe_path}")
        print(f"Executable Size:     {size_mb:.2f} MB")
        print("\nHow to run:")
        print("  1. Interactive Web GUI (Streamlit):")
        print(f'     "{exe_path}"')
        print("  2. Command-Line Experiment Pipeline:")
        print(f'     "{exe_path}" --cli')
        print("=" * 70)
    else:
        print("\n⚠️ Build completed, but executable not found at expected path.")


if __name__ == "__main__":
    build()
