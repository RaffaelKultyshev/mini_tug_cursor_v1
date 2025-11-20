from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

import numpy as np
import pandas as pd


@dataclass
class ReconSettings:
    date_window_days: int = 3
    amount_tolerance: float = 0.5
    psp_fee_abs: float = 50.0
    psp_fee_pct: float = 0.04
    only_psp_names: bool = True
    persist: bool = False


@dataclass
class ReconSummary:
    total_rule1: int
    total_rule2: int
    total_rule3: int
    recent: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReconResult:
    invoices: pd.DataFrame
    bank: pd.DataFrame
    summary: ReconSummary


def fee_ok(gross, net, fee_abs_max, fee_pct_max):
    gross = float(gross)
    net = float(net)
    fee = round(gross - net, 2)
    if fee <= 0:
        return False, 0.0
    if fee <= fee_abs_max and (gross > 0) and (fee / gross) <= fee_pct_max:
        return True, fee
    return False, 0.0


def greedy_many_to_one(open_rows, target_net, tol, fee_abs_max, fee_pct_max):
    rows = open_rows.sort_values("date")
    picked, gross_sum = [], 0.0
    for idx, r in rows.iterrows():
        if pd.notna(r.get("match_id")) and str(r.get("match_id")) != "":
            continue
        amt = float(r["amount"])
        if gross_sum + amt <= target_net + fee_abs_max:
            picked.append(int(idx))
            gross_sum += amt
        if abs(gross_sum - target_net) <= tol:
            return picked, gross_sum, 0.0, True
        ok, fee = fee_ok(gross_sum, target_net, fee_abs_max, fee_pct_max)
        if ok:
            return picked, gross_sum, fee, True
    return [], 0.0, 0.0, False


def ensure_columns(inv: pd.DataFrame, bank: pd.DataFrame):
    for c in ["match_id", "status", "invoice_no"]:
        if c not in inv.columns:
            inv[c] = pd.NA
    for c in ["match_id", "status", "partner", "memo"]:
        if c not in bank.columns:
            bank[c] = pd.NA
    return inv, bank


def run_reconciliation(inv: pd.DataFrame, bank: pd.DataFrame, settings: ReconSettings) -> ReconResult:
    if inv.empty or bank.empty:
        return ReconResult(
            invoices=inv,
            bank=bank,
            summary=ReconSummary(0, 0, 0, [])
        )

    inv = inv.copy()
    bank = bank.copy()
    inv, bank = ensure_columns(inv, bank)

    date_window = pd.Timedelta(days=settings.date_window_days)

    total_rule1 = total_rule2 = total_rule3 = 0
    recent: List[dict[str, Any]] = []

    inv_u = inv[(inv.get("type") == "revenue") & (inv["match_id"].isna())].copy()
    bank_u = bank[(bank.get("direction") == "in") & (bank["match_id"].isna())].copy()

    matches = []
    for i_idx, irow in inv_u.iterrows():
        cands = bank_u[
            (bank_u["entity"] == irow["entity"])
            & (
                bank_u["amount"].round(2).between(
                    round(irow["amount"] - settings.amount_tolerance, 2),
                    round(irow["amount"] + settings.amount_tolerance, 2),
                )
            )
            & ((bank_u["date"] - irow["date"]).abs() <= date_window)
        ]
        if len(cands) == 1:
            b_idx = cands.index[0]
            mid = f"M{i_idx}-{b_idx}"
            matches.append((i_idx, b_idx, mid))

    for i_idx, b_idx, mid in matches:
        inv.loc[i_idx, ["match_id", "status"]] = [mid, "Matched"]
        bank.loc[b_idx, ["match_id", "status"]] = [mid, "Matched"]
        recent.append(dict(rule="R1 exact", inv_id=i_idx, bank_id=b_idx, match_id=mid))
    total_rule1 = len(matches)

    inv_u2 = inv[(inv.get("type") == "revenue") & (inv["match_id"].isna())].copy()
    bank_u2 = bank[(bank.get("direction") == "in") & (bank["match_id"].isna())].copy()

    if settings.only_psp_names and ("partner" in bank_u2.columns or "memo" in bank_u2.columns):
        txtcol = "partner" if "partner" in bank_u2.columns else "memo"
        bank_u2 = bank_u2[
            bank_u2[txtcol]
            .fillna("")
            .str.contains(
                r"stripe|adyen|mollie|paypal|checkout\.com|braintree",
                case=False,
                regex=True,
            )
        ]

    psp_matches = []
    for i_idx, irow in inv_u2.iterrows():
        cands = bank_u2[
            (bank_u2["entity"] == irow["entity"])
            & ((bank_u2["date"] - irow["date"]).abs() <= date_window)
        ]
        for b_idx, brow in cands.iterrows():
            ok, fee = fee_ok(
                irow["amount"],
                brow["amount"],
                settings.psp_fee_abs,
                settings.psp_fee_pct,
            )
            if ok:
                mid = f"F{i_idx}-{b_idx}"
                psp_matches.append((i_idx, b_idx, mid))
                break

    for i_idx, b_idx, mid in psp_matches:
        inv.loc[i_idx, ["match_id", "status"]] = [mid, "Matched"]
        bank.loc[b_idx, ["match_id", "status"]] = [mid, "Matched (fee)"]
        recent.append(dict(rule="R2 fee", inv_id=i_idx, bank_id=b_idx, match_id=mid))
    total_rule2 = len(psp_matches)

    inv_u3 = inv[(inv.get("type") == "revenue") & (inv["match_id"].isna())].copy()
    bank_u3 = bank[(bank.get("direction") == "in") & (bank["match_id"].isna())].copy()

    batch_matches = []
    for b_idx, brow in bank_u3.iterrows():
        cands = inv_u3[
            (inv_u3["entity"] == brow["entity"])
            & ((inv_u3["date"] - brow["date"]).abs() <= date_window)
        ]
        if cands.empty:
            continue
        ids, gross_sum, fee, ok = greedy_many_to_one(
            cands,
            float(brow["amount"]),
            settings.amount_tolerance,
            settings.psp_fee_abs,
            settings.psp_fee_pct,
        )
        if ok and ids:
            mid = f"B{b_idx}-" + ",".join(map(str, ids))
            batch_matches.append((ids, b_idx, mid))

    for ids, b_idx, mid in batch_matches:
        inv.loc[ids, ["match_id", "status"]] = [mid, "Matched"]
        bank.loc[b_idx, ["match_id", "status"]] = [mid, "Matched (batch)"]
        recent.append(
            dict(rule="R3 batch", inv_ids=",".join(map(str, ids)), bank_id=b_idx, match_id=mid)
        )
    total_rule3 = len(batch_matches)

    summary = ReconSummary(
        total_rule1=total_rule1,
        total_rule2=total_rule2,
        total_rule3=total_rule3,
        recent=recent,
    )

    return ReconResult(invoices=inv, bank=bank, summary=summary)


