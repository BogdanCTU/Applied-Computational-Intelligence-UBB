"""Main Launcher for Bank Marketing Classifier (GUI & CLI).

Run locally:
    python run_app.py          # Launches interactive Streamlit GUI in browser
    python run_app.py --cli    # Runs end-to-end experiment pipeline in terminal

When compiled with PyInstaller, this serves as the unified Windows .exe entry point.
"""

import os
import sys
from pathlib import Path

# Determine bundle / project root
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys._MEIPASS).resolve()
    if sys.platform == "win32":
        try:
            import ctypes
            if ctypes.windll.kernel32.AttachConsole(-1):
                sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                sys.stderr = open("CONOUT$", "w", encoding="utf-8")
        except Exception:
            pass
    # Guard against None streams in macOS .app windowed mode while preserving terminal output
    if sys.stdout is None:
        try:
            sys.stdout = open("/dev/stdout", "w", encoding="utf-8")
        except Exception:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        try:
            sys.stderr = open("/dev/stderr", "w", encoding="utf-8")
        except Exception:
            sys.stderr = open(os.devnull, "w", encoding="utf-8")
else:
    ROOT_DIR = Path(__file__).resolve().parent

# Ensure project root and numbered folders are available on sys.path
for folder in [
    ROOT_DIR,
    ROOT_DIR / "1_Dataset",
    ROOT_DIR / "2_BayesianNetworkClassification",
    ROOT_DIR / "3_RuleBasedClassification",
]:
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


def run_native_gui():
    try:
        import desktop_app
        desktop_app.main()
    except (ImportError, ModuleNotFoundError) as e:
        if "tkinter" in str(e).lower() or "_tkinter" in str(e).lower():
            print("\n[Notice] Tkinter is not available in the current environment.")
            print("Launching the interactive Streamlit Web GUI instead...\n")
            run_streamlit()
        else:
            raise


def run_cli():
    print("=" * 70)
    print("UCI BANK MARKETING CLASSIFIER - COMMAND LINE INTERFACE")
    print("=" * 70)
    from src.main import main
    main()


def run_streamlit():
    import streamlit.web.bootstrap as stb

    app_path = ROOT_DIR / "app.py"

    flag_options = {
        "server.headless": False,
        "global.developmentMode": False,
        "browser.gatherUsageStats": False,
    }

    extra_args = [arg for arg in sys.argv[1:] if arg not in ("--gui", "--web")]
    stb.run(str(app_path), False, extra_args, flag_options)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        run_cli()
    elif len(sys.argv) > 1 and sys.argv[1] == "--web":
        run_streamlit()
    else:
        run_native_gui()
