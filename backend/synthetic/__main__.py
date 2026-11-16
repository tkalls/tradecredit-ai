"""Run with python -m synthetic --seed 7 --count 20 --fault-rate 0.3 --out PATH."""

import argparse
from pathlib import Path

from synthetic import generate


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--fault-rate", type=float, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        generate(seed=args.seed, count=args.count, fault_rate=args.fault_rate, out=args.out)
    except (ValueError, OSError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    main()
