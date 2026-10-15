"""Run from PyCharm or the terminal. API is the default and needs no browser."""

import argparse
from pathlib import Path

from robot import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=["api", "interview", "performance", "ui", "google", "all"], nargs="?", default="api")
    parser.add_argument("--browser", default="headlesschrome", help="Use chrome for a visible window")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    suites = {
        "api": ["api.robot"],
        "interview": ["api_interview.robot"],
        "performance": ["api_performance.robot", "performance_theory.robot"],
        "ui": ["ui_local.robot"],
        "google": ["ui_google.robot"],
        "all": ["api.robot", "api_interview.robot", "ui_local.robot"],
    }
    return run(
        *(str(root / "tests" / name) for name in suites[args.suite]),
        outputdir=str(root / "results" / args.suite),
        variable=[f"BROWSER:{args.browser}"],
    )


if __name__ == "__main__":
    raise SystemExit(main())
