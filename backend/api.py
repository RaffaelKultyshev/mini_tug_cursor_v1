from __future__ import annotations

import io
from typing import Literal

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend import core
from backend.config import get_settings
from backend.services import data_layer, ocr, reconciliation, reporting

settings = get_settings()

app = FastAPI(
    title="Mini-TUG backend",
    version="1.0.0",
    description="Backend API herbouwd uit de Streamlit app",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthcheck():
    return {"status": "ok", "has_data": data_layer.db_has_data()}


@app.get("/kpi")
def kpi():
    return core.get_kpis()


@app.post("/data/sample")
def load_sample():
    counts = data_layer.load_sample_data()
    return {"status": "ok", "counts": counts}


@app.post("/data/reset")
def reset():
    data_layer.reset_db()
    return {"status": "ok"}


@app.post("/data/upload/{dataset}")
async def upload_csv(
    dataset: Literal["invoices", "bank_tx"], file: UploadFile = File(...)
):
    content = await file.read()
    try:
        rows = data_layer.import_csv(dataset, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"dataset": dataset, "rows": rows}


@app.get("/datasets/{dataset}")
def get_dataset(dataset: Literal["invoices", "bank_tx"]):
    inv, bank = data_layer.load_data()
    df = inv if dataset == "invoices" else bank
    return {"dataset": dataset, "rows": df.to_dict("records")}


class ReconcileRequest(BaseModel):
    date_window_days: int = 3
    amount_tolerance: float = 0.5
    psp_fee_abs: float = 50.0
    psp_fee_pct: float = 4.0
    only_psp_names: bool = True
    persist: bool = False


@app.post("/reconcile")
def run_reconcile(payload: ReconcileRequest):
    inv, bank = data_layer.load_data()
    settings_obj = reconciliation.ReconSettings(
        date_window_days=payload.date_window_days,
        amount_tolerance=payload.amount_tolerance,
        psp_fee_abs=payload.psp_fee_abs,
        psp_fee_pct=payload.psp_fee_pct / 100.0,
        only_psp_names=payload.only_psp_names,
        persist=payload.persist,
    )
    result = reconciliation.run_reconciliation(inv, bank, settings_obj)
    if payload.persist:
        data_layer.persist_frames(result.invoices, result.bank)
    summary = result.summary.__dict__
    summary["recent"] = result.summary.recent
    return {
        "summary": summary,
        "invoices": len(result.invoices),
        "bank": len(result.bank),
    }


@app.post("/ocr/scan")
async def scan_invoices(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one file")
    payload = []
    for f in files:
        content = await f.read()
        payload.append((f.filename, content))
    df = ocr.process_files(payload)
    if df.empty:
        raise HTTPException(status_code=500, detail="Document AI returned no data")
    rows = data_layer.append_invoices(df)
    return {"rows_appended": rows}


@app.get("/reporting/overview")
def reporting_overview(entity: str = "ALL"):
    inv, bank = data_layer.load_data()
    overview = reporting.build_overview(inv, bank, entity)
    return overview


@app.get("/reporting/exceptions")
def reporting_exceptions():
    inv, bank = data_layer.load_data()
    return reporting.build_exceptions(inv, bank)


@app.get("/reporting/journal")
def reporting_journal():
    inv, bank = data_layer.load_data()
    journal_df = reporting.build_journal(inv, bank)
    return {"rows": journal_df.to_dict("records")}


@app.get("/reports/board-pack")
def download_board_pack():
    inv, bank = data_layer.load_data()
    blob, size = reporting.board_pack(inv, bank)
    if size == 0:
        raise HTTPException(status_code=404, detail="No data to build board pack")
    headers = {
        "Content-Disposition": 'attachment; filename="board_pack.zip"',
        "Content-Length": str(size),
    }
    return StreamingResponse(
        io.BytesIO(blob),
        media_type="application/zip",
        headers=headers,
    )
