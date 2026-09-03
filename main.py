import argparse

from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="JARVIS OS")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run the terminal interface instead of the desktop app.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.cli:
        from core.jarvis import Jarvis

        Jarvis().start()
        return

    from interface.operating_app import run_app

    raise SystemExit(run_app())


if __name__ == "__main__":
    main()
