"""Deterministic, entirely invented import-finance application packs."""

import csv
import json
import random
from decimal import Decimal
from pathlib import Path

FAULTS = ("amount_mismatch", "currency_mismatch", "missing_document", "negative_balance")
DOCUMENTS = ("application.json", "proforma_invoice.json", "bank_statement.csv")


def money(value: Decimal) -> str:
    return format(value, ".2f")


def generate(*, seed: int, count: int, fault_rate: float, out: Path) -> None:
    """Write packs without replacing existing folders or using application code."""
    if count < 0 or not 0 <= fault_rate <= 1:
        raise ValueError("count must be nonnegative and fault-rate must be between 0 and 1")
    folders = [out / f"pack-{seed}-{index:03d}" for index in range(1, count + 1)]
    for folder in folders:
        if folder.exists():
            raise FileExistsError(f"Refusing to overwrite {folder}")
    rng = random.Random(seed)  # noqa: S311 - reproducible fixtures, no security use
    for folder in folders:
        faults = [fault for fault in FAULTS if rng.random() < fault_rate]
        currency = rng.choice(("USD", "EUR", "MYR"))
        quantity = rng.randint(1, 100)
        price = Decimal(rng.randint(100, 100_000)) / 100
        total = quantity * price
        application = {
            "applicant_name": f"Zyvq-{rng.randrange(1_000_000):06d} (synthetic)",
            "facility_type": rng.choice(("lc", "import_loan", "invoice_finance")),
            "amount": money(total + (Decimal("1.00") if "amount_mismatch" in faults else 0)),
            "currency": currency,
            "tenor_days": rng.choice((30, 60, 90, 120)),
        }
        invoice = {
            "supplier_name": f"Qevz-{rng.randrange(1_000_000):06d} (synthetic)",
            "incoterm": rng.choice(("FOB", "CIF")),
            "currency": (
                rng.choice([value for value in ("USD", "EUR", "MYR") if value != currency])
                if "currency_mismatch" in faults
                else currency
            ),
            "lines": [
                {
                    "description": "Vyxq components (synthetic)",
                    "quantity": quantity,
                    "unit_price": money(price),
                    "total": money(total),
                }
            ],
            "total": money(total),
        }
        folder.mkdir(parents=True)
        for filename, content in (
            ("application.json", application),
            ("proforma_invoice.json", invoice),
        ):
            (folder / filename).write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
        balance = Decimal("0.00")
        with (folder / "bank_statement.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(("date", "description", "amount", "balance"))
            for month in range(1, 13):
                credit = Decimal(rng.randint(500_000, 900_000)) / 100
                debit = Decimal(rng.randint(100_000, 400_000)) / 100
                if month == 12 and "negative_balance" in faults:
                    debit = balance + credit + Decimal("100.00")
                for day, description, amount in (
                    (1, "Vyxq receipts (synthetic)", credit),
                    (28, "Qevz expenses (synthetic)", -debit),
                ):
                    balance += amount
                    writer.writerow(
                        (f"2025-{month:02d}-{day:02d}", description, money(amount), money(balance))
                    )
        if "missing_document" in faults:
            missing = rng.choice(DOCUMENTS)
            (folder / missing).unlink()
            hidden = (
                {"negative_balance"}
                if missing == "bank_statement.csv"
                else {"amount_mismatch", "currency_mismatch"}
            )
            faults = [fault for fault in faults if fault not in hidden]
        (folder / "truth.json").write_text(json.dumps(faults, indent=2) + "\n", encoding="utf-8")
