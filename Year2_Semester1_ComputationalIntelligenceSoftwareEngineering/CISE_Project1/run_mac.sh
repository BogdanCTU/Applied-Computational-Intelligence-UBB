#!/usr/bin/env bash
# Launcher script for Bank Marketing Classifier on macOS
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

APP_BUNDLE="$PROJECT_ROOT/dist/BankMarketingClassifier.app"
CLI_BIN="$PROJECT_ROOT/dist/BankMarketingClassifier/BankMarketingClassifier"

if [ "$1" == "--cli" ]; then
    if [ -x "$CLI_BIN" ]; then
        exec "$CLI_BIN" --cli
    else
        exec "$PROJECT_ROOT/.venv/bin/python" run_app.py --cli
    fi
elif [ "$1" == "--web" ]; then
    if [ -x "$CLI_BIN" ]; then
        exec "$CLI_BIN" --web
    else
        exec "$PROJECT_ROOT/.venv/bin/python" run_app.py --web
    fi
else
    # Default: Native Desktop Application
    if [ -d "$APP_BUNDLE" ]; then
        echo "🚀 Launching BankMarketingClassifier.app..."
        open "$APP_BUNDLE"
    elif [ -x "$CLI_BIN" ]; then
        exec "$CLI_BIN"
    else
        exec "$PROJECT_ROOT/.venv/bin/python" run_app.py
    fi
fi
