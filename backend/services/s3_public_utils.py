# services/s3_public_utils.py
import io
import re
import hashlib
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, Tuple, List
from urllib.parse import quote

S3_BUCKET = "observatorio-innovacion"
S3_REGION = "us-east-1"  # ← tu región real
S3_BASE = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com"
S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

def _encode_query_param(val: str) -> str:
    # Codifica para querystring (no para path)
    return quote(val, safe="")

def _encode_path_segment(seg: str) -> str:
    # Codifica un segmento de path, preserva caracteres seguros y NO convierte '/'
    # (esto se usa por segmento, así que no hay '/')
    return quote(seg, safe="()[]!$*-_.~'")

def s3_list(prefix: str, max_keys: int = 1000) -> List[dict]:
    """
    Lista objetos públicos de S3 bajo un prefix.
    NOTA: no pagina automáticamente; si hay más de max_keys, necesitarías manejar 'marker'.
    """
    url = f"{S3_BASE}/?prefix={_encode_query_param(prefix)}&max-keys={max_keys}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.content)

    out = []
    for ct in root.findall("s3:Contents", S3_NS):
        key = ct.findtext("s3:Key", namespaces=S3_NS) or ""
        last = ct.findtext("s3:LastModified", namespaces=S3_NS) or ""
        size_txt = ct.findtext("s3:Size", namespaces=S3_NS) or "0"
        try:
            size = int(size_txt)
        except Exception:
            size = 0
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        except Exception:
            last_dt = None
        out.append({"key": key, "last_modified": last_dt, "size": size})
    return out

def pick_latest_csv(prefix: str, pattern: Optional[str] = None) -> Optional[str]:
    items = s3_list(prefix)
    csvs = [i for i in items if i["key"].lower().endswith(".csv") and i["size"] > 0]
    if pattern:
        rx = re.compile(pattern, re.IGNORECASE)
        csvs = [i for i in csvs if rx.search(i["key"])]
    if not csvs:
        return None
    csvs.sort(key=lambda x: (x["last_modified"] or datetime.min), reverse=True)
    return csvs[0]["key"]

def build_s3_url_from_key(key: str) -> str:
    """
    Construye la URL pública HTTPS a partir de un key S3,
    codificando cada segmento por separado para no romper las '/'.
    """
    parts = [p for p in key.split("/") if p != ""]
    return f"{S3_BASE}/" + "/".join(_encode_path_segment(p) for p in parts)

def leer_csv_text(texto: str, required_column: Optional[str] = None) -> pd.DataFrame:
    for sep in [",", ";", "\t", "|"]:
        try:
            df = pd.read_csv(io.StringIO(texto), sep=sep)
            if required_column is None or required_column in df.columns:
                return df
        except Exception:
            pass
    raise ValueError("No se pudo leer el CSV con los separadores probados.")

def descargar_csv_df(url: str, required_column: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    text = resp.text
    return leer_csv_text(text, required_column=required_column), text

def hash_text(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()
