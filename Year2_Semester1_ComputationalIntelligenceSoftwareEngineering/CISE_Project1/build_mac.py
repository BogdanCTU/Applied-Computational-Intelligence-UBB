#!/usr/bin/env python3
"""Automated build script for macOS Application Bundle (.app) and executable.

Usage:
    python3 build_mac.py
    or: ./build_mac.py
    or: ./build_mac.sh
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def build():
    print("=" * 70)
    print("BUILDING BANK MARKETING CLASSIFIER MACOS APPLICATION")
    print("=" * 70)
    print(f"macOS Version:    {platform.mac_ver()[0]} ({platform.machine()})")
    print(f"Python Version:   {sys.version.split()[0]}")
    print(f"Project Root:     {PROJECT_ROOT}")

    if sys.platform != "darwin":
        print(f"\n⚠️  Warning: This build script is configured for macOS (Darwin).")
        print(f"   Current OS detected: {sys.platform}")
        print("   For Windows, run: python build_exe.py")
        sys.exit(1)

    spec_file = PROJECT_ROOT / "BankMarketingClassifier_mac.spec"
    if not spec_file.exists():
        print(f"Error: Spec file {spec_file} not found!")
        sys.exit(1)

    # Check for PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller:      v{PyInstaller.__version__}")
    except ImportError:
        print("\n❌ PyInstaller is not installed in the active environment.")
        print("   Please run: pip install 'pyinstaller>=6.22.0'")
        sys.exit(1)

    # Clean previous build artifacts
    for folder_name in ["build", "dist", ".pyinstaller_cache"]:
        folder = PROJECT_ROOT / folder_name
        if folder.exists():
            print(f"Cleaning previous {folder_name}/ folder...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Warning: Could not remove {folder}: {e}")

    # Set local cache dir to avoid macOS sandbox permission constraints
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
    print("\nCompiling macOS Application Bundle... (this may take 1-3 minutes)\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\n❌ Build failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    app_path = PROJECT_ROOT / "dist" / "BankMarketingClassifier.app"
    cli_path = PROJECT_ROOT / "dist" / "BankMarketingClassifier" / "BankMarketingClassifier"

    # Attempt ad-hoc codesigning on macOS for local execution clearance
    if app_path.exists():
        try:
            print("\nApplying ad-hoc code signature for local Gatekeeper clearance...")
            subprocess.run(
                ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print("✅ Ad-hoc signing completed.")
        except Exception as e:
            print(f"Notice: Codesign skipped: {e}")

    if app_path.exists():
        # Calculate app bundle size
        total_size = sum(f.stat().st_size for f in app_path.rglob("*") if f.is_file())
        size_mb = total_size / (1024 * 1024)

        print("\n" + "=" * 70)
        print("✅ MACOS BUILD SUCCEEDED!")
        print("=" * 70)
        print(f"App Bundle Location:   {app_path}")
        print(f"App Bundle Size:       {size_mb:.2f} MB")
        if cli_path.exists():
            print(f"Standalone CLI Binary: {cli_path}")
        print("\nHow to run on macOS (MacBook):")
        print("  1. Launch Desktop GUI:")
        print("     • Double-click 'BankMarketingClassifier.app' in Finder, or")
        print(f'     • open "{app_path}"')
        print("  2. Launch Interactive Web GUI (Streamlit):")
        print(f'     "{cli_path}" --web')
        print("  3. Run Experiment Pipeline in Terminal (CLI):")
        print(f'     "{cli_path}" --cli')
        print("\nNote for distributing to other MacBooks:")
        print("  If opened on another Mac and macOS Gatekeeper displays an untrusted prompt:")
        print(f"    Right-click 'BankMarketingClassifier.app' -> Open, or run:")
        print(f"    xattr -cr '{app_path}'")
        print("=" * 70)
    else:
        print("\n⚠️ Build finished, but expected app bundle was not found at:")
        print(f"   {app_path}")


if __name__ == "__main__":
    build()
