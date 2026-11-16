"""Check generated documents against their planted ground truth."""

import csv
import json
import re
import runpy
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from synthetic import generate
from synthetic.__main__ import main

DOCUMENTS = {"application.json", "proforma_invoice.json", "bank_statement.csv"}
FAULTS = {"amount_mismatch", "currency_mismatch", "missing_document", "negative_balance"}


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("rate", [0.0, 0.3, 1.0])
def test_documents_match_truth(tmp_path: Path, rate: float) -> None:
    generate(seed=7, count=30, fault_rate=rate, out=tmp_path)
    packs = sorted(tmp_path.iterdir())
    assert [path.name for path in packs] == [f"pack-7-{index:03d}" for index in range(1, 31)]
    seen: set[str] = set()
    missing_seen: set[str] = set()
    for pack in packs:
        faults = json.loads((pack / "truth.json").read_text())
        assert len(faults) == len(set(faults))
        assert set(faults) <= FAULTS
        seen.update(faults)
        if rate == 0:
            assert faults == []
        present = {path.name for path in pack.iterdir()}
        assert "truth.json" in present
        assert present <= DOCUMENTS | {"truth.json"}
        assert len(DOCUMENTS - present) == int("missing_document" in faults)
        missing_seen.update(DOCUMENTS - present)
        observed = {"missing_document"} if DOCUMENTS - present else set()
        application_path = pack / "application.json"
        invoice_path = pack / "proforma_invoice.json"
        if application_path.exists():
            application = json.loads(application_path.read_text())
            assert application["applicant_name"].endswith(" (synthetic)")
            assert application["facility_type"] in {"lc", "import_loan", "invoice_finance"}
            assert application["tenor_days"] > 0
            assert re.fullmatch(r"\d+\.\d{2}", application["amount"])
            assert application["currency"] in {"USD", "EUR", "MYR"}
        if invoice_path.exists():
            invoice = json.loads(invoice_path.read_text())
            assert invoice["supplier_name"].endswith(" (synthetic)")
            assert invoice["incoterm"] in {"FOB", "CIF"}
            line_totals = []
            for line in invoice["lines"]:
                assert line["description"].endswith(" (synthetic)")
                assert re.fullmatch(r"\d+\.\d{2}", line["unit_price"])
                assert Decimal(line["total"]) == line["quantity"] * Decimal(line["unit_price"])
                line_totals.append(Decimal(line["total"]))
            assert re.fullmatch(r"\d+\.\d{2}", invoice["total"])
            assert Decimal(invoice["total"]) == sum(line_totals)
        if application_path.exists() and invoice_path.exists():
            if Decimal(application["amount"]) != Decimal(invoice["total"]):
                observed.add("amount_mismatch")
            if application["currency"] != invoice["currency"]:
                observed.add("currency_mismatch")
        bank_path = pack / "bank_statement.csv"
        if bank_path.exists():
            with bank_path.open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            assert len(rows) == 24
            dates = [date.fromisoformat(row["date"]) for row in rows]
            assert dates == sorted(dates)
            assert {value.month for value in dates} == set(range(1, 13))
            balance = Decimal("0.00")
            month_ends: dict[str, Decimal] = {}
            for row in rows:
                assert row["description"].endswith(" (synthetic)")
                assert re.fullmatch(r"-?\d+\.\d{2}", row["amount"])
                assert re.fullmatch(r"-?\d+\.\d{2}", row["balance"])
                balance += Decimal(row["amount"])
                assert Decimal(row["balance"]) == balance
                month_ends[row["date"][:7]] = balance
            if any(value < 0 for value in month_ends.values()):
                observed.add("negative_balance")
        assert set(faults) == observed
        if rate == 1:
            expected = {"missing_document"}
            expected |= (
                {"amount_mismatch", "currency_mismatch"}
                if "bank_statement.csv" not in present
                else {"negative_balance"}
            )
            assert observed == expected
    assert seen == (set() if rate == 0 else FAULTS)
    if rate == 1:
        assert missing_seen == DOCUMENTS


def test_cli_is_byte_reproducible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    args = ["--seed", "7", "--count", "20", "--fault-rate", "0.3", "--out"]
    monkeypatch.setattr(sys, "argv", ["synthetic", *args, str(first)])
    monkeypatch.delitem(sys.modules, "synthetic.__main__")
    runpy.run_module("synthetic", run_name="__main__")
    main([*args, str(second)])
    assert snapshot(first) == snapshot(second)
    different = tmp_path / "different"
    generate(seed=8, count=20, fault_rate=0.3, out=different)
    assert sorted(snapshot(first).values()) != sorted(snapshot(different).values())


@pytest.mark.parametrize(("count", "rate"), [(-1, 0.3), (1, -0.1), (1, 1.1), (1, float("nan"))])
def test_invalid_options_write_nothing(tmp_path: Path, count: int, rate: float) -> None:
    with pytest.raises(SystemExit) as error:
        main(
            [
                "--seed",
                "7",
                "--count",
                str(count),
                "--fault-rate",
                str(rate),
                "--out",
                str(tmp_path),
            ]
        )
    assert error.value.code == 2
    assert list(tmp_path.iterdir()) == []


def test_existing_pack_is_preserved_before_any_writes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    existing = tmp_path / "pack-7-002"
    existing.mkdir()
    (existing / "keep.txt").write_text("keep me")
    before = snapshot(tmp_path)
    with pytest.raises(FileExistsError):
        generate(seed=7, count=2, fault_rate=1, out=tmp_path)
    with pytest.raises(SystemExit) as error:
        main(["--seed", "7", "--count", "2", "--fault-rate", "1", "--out", str(tmp_path)])
    assert error.value.code == 2
    assert f"Refusing to overwrite {existing}" in capsys.readouterr().err
    assert snapshot(tmp_path) == before
    assert not (tmp_path / "pack-7-001").exists()


def test_zero_count_is_empty(tmp_path: Path) -> None:
    generate(seed=7, count=0, fault_rate=0, out=tmp_path)
    assert list(tmp_path.iterdir()) == []
