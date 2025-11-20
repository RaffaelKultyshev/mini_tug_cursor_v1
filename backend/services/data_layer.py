from __future__ import annotations

import io
import sqlite3
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Tuple

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "mini_tug.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def list_tables() -> list[str]:
    if not DB_PATH.exists():
        return []
    with get_connection() as con:
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row[0] for row in cur.fetchall()]


def db_has_data() -> bool:
    tables = set(list_tables())
    return {"invoices", "bank_tx"}.issubset(tables)


def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not DB_PATH.exists():
        return pd.DataFrame(), pd.DataFrame()

    with get_connection() as con:
        tables = list_tables()
        inv = (
            pd.read_sql_query("SELECT * FROM invoices", con)
            if "invoices" in tables
            else pd.DataFrame()
        )
        bank = (
            pd.read_sql_query("SELECT * FROM bank_tx", con)
            if "bank_tx" in tables
            else pd.DataFrame()
        )

    inv = _normalize_dates(inv)
    bank = _normalize_dates(bank)
    return inv, bank


def _normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    if "month" not in df.columns and "date" in df.columns:
        df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df


def _ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def reset_db():
    if DB_PATH.exists():
        DB_PATH.unlink()


def load_sample_data() -> dict[str, int]:
    invoices_csv = DATA_DIR / "invoices.csv"
    bank_csv = DATA_DIR / "bank_tx.csv"
    if not invoices_csv.exists() or not bank_csv.exists():
        raise FileNotFoundError("Sample CSVs not found under /data")

    inv_df = pd.read_csv(invoices_csv, parse_dates=["date"])
    bank_df = pd.read_csv(bank_csv, parse_dates=["date"])

    inv_df["month"] = inv_df["date"].dt.to_period("M").dt.to_timestamp()
    bank_df["month"] = bank_df["date"].dt.to_period("M").dt.to_timestamp()

    inv_df = _ensure_columns(inv_df, ["match_id", "status", "invoice_no"])
    bank_df = _ensure_columns(bank_df, ["match_id", "status", "partner", "memo"])

    with get_connection() as con:
        inv_df.to_sql("invoices", con, if_exists="replace", index=False)
        bank_df.to_sql("bank_tx", con, if_exists="replace", index=False)

    return {"invoices": len(inv_df), "bank": len(bank_df)}


def import_csv(dataset: Literal["invoices", "bank_tx"], file_bytes: bytes) -> int:
    df = pd.read_csv(io.BytesIO(file_bytes), parse_dates=["date"])

    if dataset == "invoices":
        df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
        df = _ensure_columns(df, ["match_id", "status", "invoice_no", "type"])
    else:
        df = _ensure_columns(df, ["partner", "memo", "match_id", "status", "direction"])
        df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    with get_connection() as con:
        df.to_sql(dataset, con, if_exists="replace", index=False)
    return len(df)


def append_invoices(rows: pd.DataFrame) -> int:
    if rows.empty:
        return 0
    rows = _normalize_dates(rows.copy())
    rows["month"] = rows["date"].dt.to_period("M").dt.to_timestamp()
    rows = _ensure_columns(rows, ["match_id", "status", "invoice_no"])
    with get_connection() as con:
        rows.to_sql("invoices", con, if_exists="append", index=False)
    return len(rows)


def persist_frames(inv: pd.DataFrame, bank: pd.DataFrame):
    with get_connection() as con:
        inv.to_sql("invoices", con, if_exists="replace", index=False)
        bank.to_sql("bank_tx", con, if_exists="replace", index=False)


@dataclass
class BoardPack:
    journal_csv: bytes
    pnl_csv: bytes
    cash_csv: bytes
    invoices_csv: bytes
    bank_csv: bytes

    def to_zip_bytes(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("journal.csv", self.journal_csv)
            z.writestr("pl_monthly.csv", self.pnl_csv)
            z.writestr("cash_monthly.csv", self.cash_csv)
            z.writestr("invoices_raw.csv", self.invoices_csv)
            z.writestr("bank_raw.csv", self.bank_csv)
        return buf.getvalue()


def build_board_pack(
    journal_df: pd.DataFrame,
    pnl_df: pd.DataFrame,
    cash_df: pd.DataFrame,
    invoices_df: pd.DataFrame,
    bank_df: pd.DataFrame,
) -> BoardPack:
    csv_kwargs = {"index": False}
    return BoardPack(
        journal_csv=journal_df.to_csv(**csv_kwargs).encode(),
        pnl_csv=pnl_df.to_csv(**csv_kwargs).encode() if not pnl_df.empty else b"",
        cash_csv=cash_df.to_csv(**csv_kwargs).encode() if not cash_df.empty else b"",
        invoices_csv=invoices_df.to_csv(**csv_kwargs).encode(),
        bank_csv=bank_df.to_csv(**csv_kwargs).encode(),
    )


