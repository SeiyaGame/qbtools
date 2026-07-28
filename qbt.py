"""Root launcher: `python qbt.py`.

Kept thin so the whole tool lives in the `qbtools` package and can also be
run with `python -m qbtools`.
"""

from qbtools.cli import app

if __name__ == "__main__":
    app()
