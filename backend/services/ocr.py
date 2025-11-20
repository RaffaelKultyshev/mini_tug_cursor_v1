from __future__ import annotations

import base64
import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List

import pandas as pd
from google.cloud import documentai as docai
from google.oauth2 import service_account

from backend.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_KEY_PATH = BASE_DIR / "tug-docai-key.json"


def _guess_mime_type(filename: str) -> str:
    lname = filename.lower()
    if lname.endswith(".pdf"):
        return "application/pdf"
    if lname.endswith(".png"):
        return "image/png"
    if lname.endswith(".jpg") or lname.endswith(".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"


def _parse_float(val: str | float | None, default: float = 0.0) -> float:
    if val is None:
        return default
    s = str(val).strip()
    if not s:
        return default
    for token in ("EUR", "eur", "€"):
        s = s.replace(token, "")
    s = s.replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return default


def _load_credentials():
    settings = get_settings()
    if settings.docai_key_json:
        try:
            key_dict = json.loads(settings.docai_key_json)
        except json.JSONDecodeError:
            key_dict = json.loads(base64.b64decode(settings.docai_key_json))
        return service_account.Credentials.from_service_account_info(key_dict)
    key_path = settings.docai_key_path or DEFAULT_KEY_PATH
    if key_path and Path(key_path).exists():
        return service_account.Credentials.from_service_account_file(str(key_path))
    return None


@lru_cache
def get_docai_client() -> docai.DocumentProcessorServiceClient:
    credentials = _load_credentials()
    settings = get_settings()
    client_options = None
    if settings.docai_location:
        client_options = {"api_endpoint": f"{settings.docai_location}-documentai.googleapis.com"}
    if credentials:
        return docai.DocumentProcessorServiceClient(
            client_options=client_options, credentials=credentials
        )
    return docai.DocumentProcessorServiceClient(client_options=client_options)


def _processor_name() -> str:
    settings = get_settings()
    if not (settings.docai_project_id and settings.docai_processor_id):
        raise RuntimeError("Document AI settings are not configured")
    return f"projects/{settings.docai_project_id}/locations/{settings.docai_location}/processors/{settings.docai_processor_id}"


def process_invoice_document(content: bytes, filename: str) -> dict:
    client = get_docai_client()
    raw_document = docai.RawDocument(content=content, mime_type=_guess_mime_type(filename))
    request = {"name": _processor_name(), "raw_document": raw_document}
    result = client.process_document(request=request)
    return docai.Document.to_dict(result.document)


def document_to_rows(ocr_doc: dict) -> list[dict]:
    entities = {e.get("type_"): e for e in ocr_doc.get("entities", [])}

    def _val(key, default=""):
        ent = entities.get(key)
        if not ent:
            return default
        return ent.get("mention_text", default)

    invoice_date = _val("invoice_date", None)
    due_date = _val("due_date", None)
    currency = _val("currency_code", "EUR")
    supplier_name = _val("supplier_name", "")
    invoice_no = _val("invoice_id", "")
    net_amount = _parse_float(_val("subtotal", "0"))
    vat_amount = _parse_float(_val("total_tax_amount", "0"))
    gross_amount = _parse_float(_val("total_amount", "0"))

    row = {
        "date": pd.to_datetime(invoice_date) if invoice_date else pd.NaT,
        "due_date": pd.to_datetime(due_date) if due_date else pd.NaT,
        "amount": gross_amount,
        "net_amount": net_amount,
        "vat_amount": vat_amount,
        "currency": currency,
        "partner": supplier_name,
        "invoice_no": invoice_no,
        "type": "expense",
        "entity": "TUG_NL",
        "source": "ocr",
        "raw_ocr": json.dumps(ocr_doc),
    }
    return [row]


def process_files(files: Iterable[tuple[str, bytes]]) -> pd.DataFrame:
    rows: list[dict] = []
    for filename, content in files:
        document = process_invoice_document(content, filename)
        rows.extend(document_to_rows(document))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


