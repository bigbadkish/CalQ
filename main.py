from __future__ import annotations

from ui import run_app


def main() -> None:
    """
    Main entry point for the CalQ application.

    Keeps the code import-safe for future extensions (e.g., using CalQ
    logic in a web app) by only running the GUI when executed directly.
    """
    run_app()


if __name__ == "__main__":
    main()