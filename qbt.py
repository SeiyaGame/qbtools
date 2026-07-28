"""Root launcher: `python qbt.py`.

Kept thin so the whole tool lives in the `qbt_trackers` package and can also be
run with `python -m qbt_trackers`.
"""

from qbt_trackers.cli import app

if __name__ == "__main__":
    app()
