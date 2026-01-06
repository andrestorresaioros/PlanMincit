# services/convocatorias_loader.py
import random
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import pandas as pd
from .s3_public_utils import (
    pick_latest_csv, build_s3_url_from_key,
    descargar_csv_df, hash_text
)

CONVOCATORIAS_PREFIX = "Convocatorias/"
CONVOCATORIAS_CSV_REGEX = r"Convocatoria|Planificaci[oó]n"
INDEX_COLUMN = "Entidad Convocante"

_CACHE_DF: Optional[pd.DataFrame] = None
_CACHE_RAW_HASH: Optional[str] = None
_CACHE_LAST_FETCH: Optional[datetime] = None
_CACHE_TTL = timedelta(minutes=10)

# === utilidades para imagen (no rompen si fallan) ===
_IMG_HINTS = re.compile(r"(imagen|logo|picture|image|foto)", re.IGNORECASE)
_IMG_URL_RE = re.compile(r"^https?://.+\.(png|jpe?g|webp|gif|svg)(\?.*)?$", re.IGNORECASE)
_IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")

def _to_public_image_url(val: str) -> Optional[str]:
    try:
        if not val:
            return None
        v = str(val).strip()
        if not v:
            return None
        if v.lower().startswith("http://") or v.lower().startswith("https://"):
            return v
        if any(v.lower().endswith(ext) for ext in _IMG_EXTS):
            return build_s3_url_from_key(v)
    except Exception:
        pass
    return None

def _pick_image_for_row(row: Dict[str, Any], columns: List[str]) -> Optional[str]:
    # 1) columnas “imagen/logo…”
    try:
        for col in columns:
            if _IMG_HINTS.search(col):
                url = _to_public_image_url(row.get(col))
                if url:
                    return url
    except Exception:
        pass

    # 2) buscar en todos los valores un URL o key de imagen
    try:
        for col in columns:
            val = str(row.get(col, "")).strip()
            if not val:
                continue
            if _IMG_URL_RE.match(val):
                return val
            if any(val.lower().endswith(ext) for ext in _IMG_EXTS):
                url = _to_public_image_url(val)
                if url:
                    return url
    except Exception:
        pass

    return None
# === fin utilidades de imagen ===

def _discover_csv_url() -> str:
    # Volvemos a la lógica original y simple
    key = pick_latest_csv(CONVOCATORIAS_PREFIX, pattern=CONVOCATORIAS_CSV_REGEX)
    if not key:
        raise RuntimeError("No se encontró CSV de Convocatorias en S3.")
    return build_s3_url_from_key(key)

def _get_df(force: bool = False) -> pd.DataFrame:
    global _CACHE_DF, _CACHE_RAW_HASH, _CACHE_LAST_FETCH

    if (
        not force and _CACHE_DF is not None and _CACHE_LAST_FETCH is not None
        and datetime.now() - _CACHE_LAST_FETCH < _CACHE_TTL
    ):
        return _CACHE_DF

    url = _discover_csv_url()
    df, raw = descargar_csv_df(url, required_column=INDEX_COLUMN)
    h = hash_text(raw)

    if not force and _CACHE_RAW_HASH == h and _CACHE_DF is not None:
        _CACHE_LAST_FETCH = datetime.now()
        return _CACHE_DF

    _CACHE_DF = df
    _CACHE_RAW_HASH = h
    _CACHE_LAST_FETCH = datetime.now()
    return _CACHE_DF

def get_resumen_por_entidad() -> List[Dict]:
    df = _get_df()
    col_nombre = "Nombre de la Convocatoria"
    col_url = "URL Oficial"

    resumen = []
    for entidad in df[INDEX_COLUMN].dropna().astype(str).str.strip().unique():
        subset = df[df[INDEX_COLUMN].astype(str).str.strip() == entidad]
        nombres = subset.get(col_nombre, pd.Series([], dtype=str)).dropna().astype(str).tolist()
        urls = subset.get(col_url, pd.Series([], dtype=str)).dropna().astype(str).tolist()
        ejemplo = nombres[0] if nombres else "Convocatoria disponible"
        resumen.append({
            "entidad": entidad,
            "descripcion": f"Una convocatoria destacada es: {ejemplo}",
            "total": int(len(subset)),
            "ejemplo": ejemplo,
            "urls": urls[:3],
        })
    resumen.sort(key=lambda x: x["total"], reverse=True)
    return resumen

def get_listado_completo() -> Dict[str, Any]:
    """
    Nunca revienta: si algo falla con el CSV, responde 200 con rows: [] y un 'error' para debug.
    """
    try:
        df = _get_df()
        columns = list(df.columns)
        rows = df.fillna("").to_dict(orient="records")

        # Añadimos __card_image sin romper si falla
        for r in rows:
            try:
                url = _pick_image_for_row(r, columns)
            except Exception:
                url = None
            r["__card_image"] = url or ""

        if "__card_image" not in columns:
            columns.append("__card_image")

        return {
            "columns": columns,
            "rows": rows,
            "source": "S3",
        }

    except Exception as e:
        # NO devolvemos 500. Entrega vacío para que el front no se muera.
        print(f"[convocatorias] Error get_listado_completo: {e}")
        return {
            "columns": [INDEX_COLUMN, "__card_image"],
            "rows": [],
            "source": "error",
            "error": str(e),
        }

def get_convocatorias_aleatorias(limit=3):
    data = get_listado_completo()
    todas = data.get("rows", [])
    if not todas:
        return []
    return random.sample(todas, min(len(todas), limit))

def listar_publico_unificado(convocatorias_db: list) -> dict:
    """
    Unifica convocatorias de la BD con las del CSV de S3.
    Similar a biblioteca_loader.listar_publico_unificado().
    
    Args:
        convocatorias_db: Lista de modelos Convocatoria de la BD
    
    Returns:
        dict con {columns, rows, source_info}
    """
    # 1. Obtener convocatorias del CSV
    data_csv = get_listado_completo()
    csv_rows = data_csv.get("rows", [])
    csv_columns = data_csv.get("columns", [])
    
    # 2. Convertir convocatorias de BD a formato dict
    bd_rows = []
    for conv in convocatorias_db:
        row = {
            "Nombre de la Convocatoria": conv.nombre_convocatoria or "",
            "Entidad Convocante": conv.entidad_convocante or "",
            "URL Oficial": conv.url_oficial or "",
            "País / Región": conv.pais_region or "",
            "Nivel Geográfico": conv.nivel_geografico or "",
            "Ámbito Temático": conv.ambito_tematico or "",
            "Público Objetivo": conv.publico_objetivo or "",
            "Etapa del Proyecto": conv.etapa_proyecto or "",
            "Frecuencia / Ciclo": conv.frecuencia_ciclo or "",
            "Fechas aproximadas": conv.fechas_aproximadas or "",
            "Financiamiento o Beneficio": conv.financiamiento_beneficio or "",
            "Formato de Participación": conv.formato_participacion or "",
            "Observaciones": conv.observaciones or "",
            "imagen url": conv.imagen_url or "",
            "__card_image": conv.imagen_url or "",  # Usar la misma imagen
            "__source": "BD",
            "__id": conv.id,  # Para poder editar/eliminar
        }
        bd_rows.append(row)
    
    # 3. Marcar filas del CSV con su fuente
    for row in csv_rows:
        row["__source"] = "CSV"
    
    # 4. Combinar ambas listas (BD primero para que aparezcan arriba)
    all_rows = bd_rows + csv_rows
    
    # 5. Asegurar que las columnas incluyan todos los campos
    all_columns = list(csv_columns)
    if "__source" not in all_columns:
        all_columns.append("__source")
    if "__id" not in all_columns:
        all_columns.append("__id")
    
    return {
        "columns": all_columns,
        "rows": all_rows,
        "source_info": {
            "total": len(all_rows),
            "bd_count": len(bd_rows),
            "csv_count": len(csv_rows),
        }
    }