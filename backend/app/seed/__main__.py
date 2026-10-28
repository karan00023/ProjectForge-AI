"""Load (or reload) the synthetic demo dataset: `python -m app.seed`."""

import argparse
from datetime import UTC, date, datetime

from app.db import get_sessionmaker
from app.seed.demo import reset_demo, seed_demo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", type=date.fromisoformat, help="anchor date (default: today)")
    parser.add_argument("--reset-only", action="store_true", help="remove demo data and exit")
    args = parser.parse_args()
    with get_sessionmaker()() as db, db.begin():
        if args.reset_only:
            reset_demo(db)
            print("Demo data removed.")
            return
        today = args.today or datetime.now(UTC).date()
        seed_demo(db, today)
    print(f"Demo data loaded (anchored to {today}). Password for all demo users: projectforge-demo")


if __name__ == "__main__":
    main()
