from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .data_layer import build_board_pack


def _group_revenue_expense(inv: pd.DataFrame) -> pd.DataFrame:
    required = {"type", "amount", "month", "entity"}
    if inv.empty or not required.issubset(inv.columns):
        return pd.DataFrame()
    revexp = (
        inv.assign(
            revenue=np.where(inv["type"].eq("revenue"), inv["amount"], 0.0),
            expense=np.where(inv["type"].eq("expense"), inv["amount"], 0.0),
        )
        .groupby(["entity", "month"], as_index=False)[["revenue", "expense"]]
        .sum()
    )
    revexp_all = (
        revexp.groupby("month", as_index=False)[["revenue", "expense"]]
        .sum()
        .assign(entity="ALL")
    )
    return pd.concat([revexp, revexp_all], ignore_index=True)


def _group_cash(bank: pd.DataFrame) -> pd.DataFrame:
    required = {"direction", "amount", "month", "entity"}
    if bank.empty or not required.issubset(bank.columns):
        return pd.DataFrame()
    bank2 = bank.copy()
    bank2["inflow"] = np.where(bank2["direction"].eq("in"), bank2["amount"], 0.0)
    bank2["outflow"] = np.where(bank2["direction"].eq("out"), bank2["amount"], 0.0)
    cash = (
        bank2.groupby(["entity", "month"], as_index=False)[["inflow", "outflow"]]
        .sum()
        .assign(net_cash=lambda d: d["inflow"] - d["outflow"])
    )
    cash_all = (
        cash.groupby("month", as_index=False)[["inflow", "outflow", "net_cash"]]
        .sum()
        .assign(entity="ALL")
    )
    return pd.concat([cash, cash_all], ignore_index=True)


def build_overview(inv: pd.DataFrame, bank: pd.DataFrame, entity: str = "ALL") -> dict:
    inv = inv.copy()
    bank = bank.copy()
    if not inv.empty and "entity" not in inv.columns:
        inv["entity"] = "TUG_NL"
    if not bank.empty and "entity" not in bank.columns:
        bank["entity"] = "TUG_NL"

    revexp = _group_revenue_expense(inv)
    cash = _group_cash(bank)

    if not revexp.empty:
        re_ent = revexp[revexp["entity"].eq(entity)].sort_values("month")
    else:
        re_ent = pd.DataFrame()

    if not cash.empty:
        cash_ent = cash[cash["entity"].eq(entity)].sort_values("month")
    else:
        cash_ent = pd.DataFrame()

    matched_inv = inv[(inv.get("type") == "revenue") & (inv["match_id"].notna())].copy()
    unmatched_inv = inv[(inv.get("type") == "revenue") & (inv["match_id"].isna())].copy()

    if not re_ent.empty:
        last_rev = re_ent["revenue"].iloc[-1]
        last_exp = re_ent["expense"].iloc[-1]
    else:
        last_rev = last_exp = 0.0

    gross_prof = last_rev - last_exp
    cash_balance = (
        cash_ent["net_cash"].cumsum().iloc[-1] if not cash_ent.empty else 0.0
    )
    prev_burn = (
        abs(cash_ent["net_cash"].shift(1).iloc[-1])
        if len(cash_ent) > 1 and cash_ent["net_cash"].shift(1).iloc[-1] < 0
        else 0.0
    )
    runway_months = (
        (cash_balance / max(1.0, prev_burn)) if prev_burn > 0 else None
    )

    matched_amt = float(matched_inv["amount"].sum()) if not matched_inv.empty else 0.0
    unmatched_amt = (
        float(unmatched_inv["amount"].sum()) if not unmatched_inv.empty else 0.0
    )
    matched_cnt = int(matched_inv.shape[0])
    unmatched_cnt = int(unmatched_inv.shape[0])
    total_revenue = float(re_ent["revenue"].sum()) if not re_ent.empty else 0.0
    collection_rate = matched_amt / total_revenue if total_revenue > 0 else 0.0

    vat_total = float(inv.get("vat_amount", pd.Series([], dtype=float)).sum())
    currencies = (
        sorted(
            inv.get("currency", pd.Series(dtype=str))
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        if not inv.empty and "currency" in inv.columns
        else []
    )

    accrual_series = (
        re_ent[["month", "revenue"]].set_index("month") if not re_ent.empty else pd.DataFrame()
    )
    if not matched_inv.empty:
        matched_m = (
            matched_inv.assign(
                month=pd.to_datetime(matched_inv["date"])
                .dt.to_period("M")
                .dt.to_timestamp()
            )
            .groupby("month", as_index=True)["amount"]
            .sum()
            .to_frame("matched_revenue")
        )
    else:
        matched_m = pd.DataFrame(columns=["matched_revenue"])

    both = accrual_series.join(matched_m, how="outer").fillna(0.0)
    rev_vs_collected = (
        both.reset_index()
        .melt(
            id_vars=["month"],
            value_vars=["revenue", "matched_revenue"],
            var_name="metric",
            value_name="amount",
        )
        .to_dict("records")
        if not both.empty
        else []
    )

    if {"month", "net_amount", "vat_amount"}.issubset(inv.columns):
        net_vat_df = (
            inv.groupby("month", as_index=False)[["net_amount", "vat_amount"]]
            .sum()
            .rename(columns={"net_amount": "Net revenue", "vat_amount": "VAT"})
            .melt(
                id_vars=["month"],
                value_vars=["Net revenue", "VAT"],
                var_name="metric",
                value_name="amount",
            )
        )
        net_vat = net_vat_df.to_dict("records")
    else:
        net_vat = []

    overview = {
        "kpis": {
            "matched_count": matched_cnt,
            "matched_amount": matched_amt,
            "unmatched_amount": unmatched_amt,
            "runway_months": runway_months,
            "vat_total": vat_total,
            "currencies": currencies,
            "gross_profit": gross_prof,
            "cash_balance": cash_balance,
            "collection_rate": collection_rate,
        },
        "rev_vs_collected": rev_vs_collected,
        "net_vat": net_vat,
        "revenue_table": re_ent.to_dict("records"),
        "cash_table": cash_ent.to_dict("records"),
        "top_ar": unmatched_inv.sort_values("amount", ascending=False)
        .head(5)
        .to_dict("records"),
    }
    return overview


def build_exceptions(inv: pd.DataFrame, bank: pd.DataFrame) -> dict:
    unmatched_invoices = (
        inv.query("type=='revenue' and match_id.isna()")
        if {"type", "match_id"}.issubset(inv.columns)
        else pd.DataFrame()
    )
    unmatched_bank = (
        bank.query("direction=='in' and match_id.isna()")
        if {"direction", "match_id"}.issubset(bank.columns)
        else pd.DataFrame()
    )
    partial = (
        bank[bank["status"].fillna("").str.contains("fee|batch|Partial", case=False)]
        if "status" in bank.columns
        else pd.DataFrame()
    )
    return {
        "unmatched_invoices": unmatched_invoices.to_dict("records"),
        "unmatched_bank": unmatched_bank.to_dict("records"),
        "psp_batch": partial.to_dict("records"),
    }


def build_journal(inv: pd.DataFrame, bank: pd.DataFrame) -> pd.DataFrame:
    COA = {
        "Revenue": "4000-Revenue",
        "Cash": "1000-Cash",
        "AR": "1200-Accounts Receivable",
        "PSP Fees": "6060-Payment Processing Fees",
    }

    journal = []

    def matched_bank_amount_and_fee(inv_row):
        mid = inv_row.get("match_id")
        if pd.isna(mid):
            return None, 0.0
        b = bank.loc[bank["match_id"] == mid]
        if b.empty:
            return None, 0.0
        bank_amt = float(b.iloc[0]["amount"])
        is_fee_context = "fee" in str(b.iloc[0]["status"]).lower() or "fee" in str(
            inv_row.get("status", "")
        ).lower()
        fee = max(0.0, float(inv_row["amount"]) - bank_amt) if is_fee_context else 0.0
        return bank_amt, fee

    for _, r in inv.dropna(subset=["match_id"]).iterrows():
        bank_amt, fee = matched_bank_amount_and_fee(r)
        if bank_amt is None:
            journal += [
                dict(
                    date=r["date"],
                    entity=r.get("entity", ""),
                    account=COA["AR"],
                    debit=float(r["amount"]),
                    credit=0.0,
                    ref="UNRESOLVED",
                ),
                dict(
                    date=r["date"],
                    entity=r.get("entity", ""),
                    account=COA["Revenue"],
                    debit=0.0,
                    credit=float(r["amount"]),
                    ref="UNRESOLVED",
                ),
            ]
            continue
        journal += [
            dict(
                date=r["date"],
                entity=r.get("entity", ""),
                account=COA["Cash"],
                debit=float(bank_amt),
                credit=0.0,
                ref=r["match_id"],
            ),
            dict(
                date=r["date"],
                entity=r.get("entity", ""),
                account=COA["Revenue"],
                debit=0.0,
                credit=float(r["amount"]),
                ref=r["match_id"],
            ),
        ]
        if fee > 0.0001:
            journal.append(
                dict(
                    date=r["date"],
                    entity=r.get("entity", ""),
                    account=COA["PSP Fees"],
                    debit=float(fee),
                    credit=0.0,
                    ref=r["match_id"],
                )
            )

    for _, r in inv[(inv.get("type") == "revenue") & (inv["match_id"].isna())].iterrows():
        journal += [
            dict(
                date=r["date"],
                entity=r.get("entity", ""),
                account=COA["AR"],
                debit=float(r["amount"]),
                credit=0.0,
                ref="UNMATCHED",
            ),
            dict(
                date=r["date"],
                entity=r.get("entity", ""),
                account=COA["Revenue"],
                debit=0.0,
                credit=float(r["amount"]),
                ref="UNMATCHED",
            ),
        ]

    return pd.DataFrame(journal)


def board_pack(inv: pd.DataFrame, bank: pd.DataFrame) -> Tuple[bytes, int]:
    revexp = _group_revenue_expense(inv)
    cash = _group_cash(bank)
    pnl_df = (
        revexp.groupby("month", as_index=False)[["revenue", "expense"]].sum()
        if not revexp.empty
        else pd.DataFrame()
    )
    cash_df = (
        cash.groupby("month", as_index=False)[["net_cash"]].sum()
        if not cash.empty
        else pd.DataFrame()
    )
    journal = build_journal(inv, bank)
    pack = build_board_pack(journal, pnl_df, cash_df, inv, bank)
    blob = pack.to_zip_bytes()
    return blob, len(blob)


