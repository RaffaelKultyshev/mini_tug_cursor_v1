# core.py — pure Python logica voor Mini_TUG (geen Streamlit)

import numpy as np
import pandas as pd

from backend.services import data_layer


def load_data():
    return data_layer.load_data()


def get_kpis():
    """
    Basis-KPIs voor de Next.js frontend.

    Geeft een dict terug met:
    - invoices_count
    - bank_count
    - total_revenue
    - collection_rate
    """
    inv, bank = load_data()

    # Aantallen rijen
    invoices_count = int(len(inv))
    bank_count = int(len(bank))

    # Totale omzet = som van amount voor revenue-invoices
    if not inv.empty and "type" in inv.columns and "amount" in inv.columns:
        revenue_rows = inv[inv["type"] == "revenue"].copy()
        total_revenue = float(revenue_rows["amount"].sum())
    else:
        revenue_rows = pd.DataFrame()
        total_revenue = 0.0

    # Collection rate = matched revenue / totale revenue
    if (
        not revenue_rows.empty
        and "match_id" in revenue_rows.columns
        and "amount" in revenue_rows.columns
    ):
        matched_rows = revenue_rows[revenue_rows["match_id"].notna()]
        matched_amt = float(matched_rows["amount"].sum()) if not matched_rows.empty else 0.0
        total_rev_all = float(revenue_rows["amount"].sum())
        collection_rate = matched_amt / total_rev_all if total_rev_all > 0 else 0.0
    else:
        collection_rate = 0.0

    return {
        "invoices_count": invoices_count,
        "bank_count": bank_count,
        "total_revenue": float(total_revenue),
        "collection_rate": float(collection_rate),
    }
