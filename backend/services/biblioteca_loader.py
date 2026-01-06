# services/biblioteca_loader.py
"""
Servicio optimizado para cargar y servir recursos de biblioteca.

OPTIMIZACIONES IMPLEMENTADAS:
1. Cache agresivo de 2 horas para CSV y índice de imágenes
2. Pre-procesamiento y cache de items CSV mapeados (_CACHE_CSV_ITEMS)
3. Carga lazy del índice de imágenes (solo cuando se necesita)
4. Paginación eficiente usando slicing sobre lista cacheada
5. Endpoint /refresh-cache para precalentar datos

RENDIMIENTO:
- Primera carga: ~2-3s (descarga CSV + procesa imágenes)
- Cargas subsecuentes: ~50-200ms (todo desde cache)
- Cache TTL: 2 horas (configurable)
"""
import os
import re
import difflib
import unicodedata
from urllib.parse import urlparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import pandas as pd

from .s3_public_utils import (
    pick_latest_csv, build_s3_url_from_key,
    descargar_csv_df, hash_text, leer_csv_text, s3_list
)

# ===== NUEVO: imports para leer publicados desde BD =====
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.biblioteca import Biblioteca

BIBLIOTECA_PREFIX = "Biblioteca/"
BIBLIOTECA_IMAGES_PREFIX = "Biblioteca/images/"
BIBLIOTECA_CSV_REGEX = r"Biblioteca|Contenidos"
BIBLIOTECA_LOCAL_BACKUP = "data/static/biblioteca_backup.csv"

COL_TIPO = "Tipo de recurso"
COL_TITULO = "Descripción / Uso sugerido"

# -------------------------
# Cache CSV
# -------------------------
_CACHE_DF: Optional[pd.DataFrame] = None
_CACHE_RAW_HASH: Optional[str] = None
_CACHE_LAST_FETCH: Optional[datetime] = None
_CACHE_TTL = timedelta(hours=2)  # Aumentado de 10 min a 2 horas

# -------------------------
# Cache índice de imágenes
# -------------------------
_IMG_INDEX: Optional[Dict[str, str]] = None  # basename_normalizado -> URL completa
_IMG_INDEX_LAST_FETCH: Optional[datetime] = None
_IMG_INDEX_TTL = timedelta(hours=2)  # Aumentado de 15 min a 2 horas

# -------------------------
# Cache de items procesados (CSV pre-mapeado)
# -------------------------
_CACHE_CSV_ITEMS: Optional[List[Dict[str, Any]]] = None
_CACHE_CSV_ITEMS_LAST_FETCH: Optional[datetime] = None

# -------------------------
# Utilidades de normalización
# -------------------------
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))

def _norm(s: str) -> str:
    s = _strip_accents(s).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9\-.]", "", s)
    return s

def _basename(key: str) -> str:
    return (key or "").rsplit("/", 1)[-1]

def _ext(s: str) -> str:
    return s.rsplit(".", 1)[-1].lower() if "." in s else ""

def _slugify_local(s: str) -> str:
    s = _strip_accents((s or "").strip().lower())
    s = re.sub(r"https?://", "", s)
    s = re.sub(r"[^a-z0-9\-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "recurso"

# -------------------------
# Descubrimiento / carga CSV
# -------------------------
def _discover_csv_url() -> str:
    key = pick_latest_csv(BIBLIOTECA_PREFIX, pattern=BIBLIOTECA_CSV_REGEX)
    if not key:
        raise RuntimeError("No se encontró CSV de Biblioteca en S3.")
    return build_s3_url_from_key(key)

def _download_or_backup() -> Tuple[pd.DataFrame, str]:
    try:
        url = _discover_csv_url()
        df, raw = descargar_csv_df(url, required_column=COL_TIPO)
        os.makedirs(os.path.dirname(BIBLIOTECA_LOCAL_BACKUP), exist_ok=True)
        with open(BIBLIOTECA_LOCAL_BACKUP, "w", encoding="utf-8") as f:
            f.write(raw)
        return df, raw
    except Exception:
        if os.path.exists(BIBLIOTECA_LOCAL_BACKUP):
            with open(BIBLIOTECA_LOCAL_BACKUP, "r", encoding="utf-8") as f:
                raw = f.read()
            df = leer_csv_text(raw, required_column=COL_TIPO)
            return df, raw
        raise

def _get_df(force: bool = False) -> pd.DataFrame:
    global _CACHE_DF, _CACHE_RAW_HASH, _CACHE_LAST_FETCH
    if (
        not force and _CACHE_DF is not None and _CACHE_LAST_FETCH is not None
        and datetime.now() - _CACHE_LAST_FETCH < _CACHE_TTL
    ):
        return _CACHE_DF

    df, raw = _download_or_backup()
    h = hash_text(raw)

    if not force and _CACHE_RAW_HASH == h and _CACHE_DF is not None:
        _CACHE_LAST_FETCH = datetime.now()
        return _CACHE_DF

    _CACHE_DF = df
    _CACHE_RAW_HASH = h
    _CACHE_LAST_FETCH = datetime.now()
    return _CACHE_DF

# -------------------------
# Índice de imágenes (S3/Biblioteca/images/)
# -------------------------
def _ensure_img_index(force: bool = False) -> Dict[str, str]:
    global _IMG_INDEX, _IMG_INDEX_LAST_FETCH

    if (
        not force and _IMG_INDEX is not None and _IMG_INDEX_LAST_FETCH is not None
        and datetime.now() - _IMG_INDEX_LAST_FETCH < _IMG_INDEX_TTL
    ):
        return _IMG_INDEX

    listing = s3_list(BIBLIOTECA_IMAGES_PREFIX)
    idx: Dict[str, str] = {}
    for it in listing:
        key = it.get("key") or ""
        size = int(it.get("size") or 0)
        if size <= 0:
            continue
        if not key.lower().startswith(BIBLIOTECA_IMAGES_PREFIX.lower()):
            continue
        base = _basename(key)
        if _ext(base) not in {"png", "jpg", "jpeg", "webp"}:
            continue
        url = build_s3_url_from_key(f"{BIBLIOTECA_IMAGES_PREFIX}{base}")
        idx[_norm(base)] = url

    _IMG_INDEX = idx
    _IMG_INDEX_LAST_FETCH = datetime.now()
    return _IMG_INDEX

# -------------------------
# Heurísticas imagen
# -------------------------
def _host_token(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
    host = re.sub(r"^www\.", "", host)
    token = host.split(".")[0]
    return _norm(token)

def _best_image_for_row(row: Dict[str, Any], img_index: Optional[Dict[str, str]] = None) -> Optional[str]:
    # Primero revisar si hay una imagen explícita en el CSV
    for cname in ["Imagen", "Image", "Img", "image", "image_url", "URL de imagen", "Imagen archivo"]:
        val = str(row.get(cname, "")).strip()
        if not val:
            continue
        if val.startswith("http://") or val.startswith("https://"):
            return val.replace("http://", "https://", 1)
        base = _basename(val)
        base_norm = _norm(base)
        # Solo cargar índice si es necesario
        if img_index is None:
            img_index = _ensure_img_index()
        if base_norm in img_index:
            return img_index[base_norm]
        return build_s3_url_from_key(f"{BIBLIOTECA_IMAGES_PREFIX}{base}")

    # Cargar índice solo si llegamos aquí (matching heurístico)
    if img_index is None:
        img_index = _ensure_img_index()
    
    titulo = str(row.get(COL_TITULO, "") or row.get("Título", "") or row.get("Titulo", ""))
    enlace = str(row.get("Enlace") or row.get("URL") or row.get("URL Oficial") or "")
    tipo   = str(row.get("Tipo de recurso", "") or row.get("Tipo", ""))
    categ  = str(row.get("Categoría temática", "") or row.get("Categoria tematica", ""))

    t_norm = _norm(titulo)
    host_tok = _host_token(enlace) if enlace.startswith("http") else ""

    path_tokens: List[str] = []
    if enlace.startswith("http"):
        try:
            p = urlparse(enlace)
            raw_parts = re.split(r"[\/\-\._]+", (p.path or ""))
            path_tokens = [tok for tok in (_strip_accents(x).lower().strip() for x in raw_parts) if len(tok) >= 4]
        except Exception:
            path_tokens = []

    text_blobs = [titulo, row.get("Autor/es", ""), row.get("Autores", ""), row.get("Autor", ""), categ, tipo]
    content_tokens: List[str] = []
    for blob in text_blobs:
        for tok in re.split(r"[^\w]+", _strip_accents(str(blob)).lower()):
            tok = tok.strip()
            if len(tok) >= 4:
                content_tokens.append(tok)
    token_set = set(content_tokens)

    familia_map = {
        "herramienta": ["herra", "herramient"],
        "manual": ["man"],
        "investigacion": ["invesacad", "investig"],
        "portal": ["portainter", "portalinter", "porta"],
        "audiovisual": ["cont-aud", "video", "podc"]
    }
    fam_keys = []
    low = (tipo + " " + categ).lower()
    if "herramient" in low: fam_keys.append("herramienta")
    if "manual" in low or "técnico" in low or "tecnico" in low: fam_keys.append("manual")
    if "investig" in low or "acad" in low: fam_keys.append("investigacion")
    if "portal" in low or "internacional" in low: fam_keys.append("portal")
    if "audio" in low or "podc" in low or "video" in low: fam_keys.append("audiovisual")
    fam_prefixes = [p for k in fam_keys for p in familia_map.get(k, [])]

    best_url = None
    best_score = 0.0

    for base_norm, url in img_index.items():
        domain_bonus = 1.0 if (host_tok and host_tok in base_norm) else 0.0
        base_tokens = set(re.split(r"[-_.]+", base_norm))
        inter = token_set & base_tokens
        union = token_set | base_tokens if token_set or base_tokens else {"_"}
        jacc = len(inter) / max(1, len(union))
        ratio = difflib.SequenceMatcher(None, t_norm, base_norm).ratio()
        path_hit = 1.0 if any(t in base_norm for t in path_tokens) else 0.0
        fam_bonus = 1.0 if any(pref in base_norm for pref in fam_prefixes) else 0.0
        score = (0.5 * domain_bonus) + (0.3 * jacc) + (0.2 * ratio) + (0.10 * path_hit) + (0.15 * fam_bonus)
        if score > best_score:
            best_score = score
            best_url = url

    if not best_url:
        for base_norm, url in img_index.items():
            if t_norm[:20] and t_norm[:20] in base_norm:
                return url
        for base_norm, url in img_index.items():
            if t_norm[:12] and t_norm[:12] in base_norm:
                return url
        head = t_norm.split("-")[0]
        if head:
            for base_norm, url in img_index.items():
                if head in base_norm:
                    return url

    return best_url

# -------------------------
# AUDITORÍA (debug)
# -------------------------
def _img_candidates_for_row(row: Dict[str, Any], img_index: Dict[str, str], top_k: int = 5):
    titulo = str(row.get(COL_TITULO, "") or row.get("Título", "") or row.get("Titulo", ""))
    enlace = str(row.get("Enlace") or row.get("URL") or row.get("URL Oficial") or "")
    tipo   = str(row.get("Tipo de recurso", "") or row.get("Tipo", ""))
    categ  = str(row.get("Categoría temática", "") or row.get("Categoria tematica", ""))

    t_norm = _norm(titulo)
    host_tok = _host_token(enlace) if enlace.startswith("http") else ""

    path_tokens: List[str] = []
    if enlace.startswith("http"):
        try:
            p = urlparse(enlace)
            raw_parts = re.split(r"[\/\-\._]+", (p.path or ""))
            path_tokens = [tok for tok in (_strip_accents(x).lower().strip() for x in raw_parts) if len(tok) >= 4]
        except Exception:
            path_tokens = []

    text_blobs = [titulo, row.get("Autor/es", ""), row.get("Autores", ""), row.get("Autor", ""), categ, tipo]
    tokens = []
    for b in text_blobs:
        for t in re.split(r"[^\w]+", _strip_accents(str(b)).lower()):
            t = t.strip()
            if len(t) >= 4:
                tokens.append(t)
    token_set = set(tokens)

    familia_map = {
        "herramienta": ["herra", "herramient"],
        "manual": ["man"],
        "investigacion": ["invesacad", "investig"],
        "portal": ["portainter", "portalinter", "porta"],
        "audiovisual": ["cont-aud", "video", "podc"]
    }
    low = (tipo + " " + categ).lower()
    fam_keys = []
    if "herramient" in low: fam_keys.append("herramienta")
    if "manual" in low or "técnico" in low or "tecnico" in low: fam_keys.append("manual")
    if "investig" in low or "acad" in low: fam_keys.append("investigacion")
    if "portal" in low or "internacional" in low: fam_keys.append("portal")
    if "audio" in low or "podc" in low or "video" in low: fam_keys.append("audiovisual")
    fam_prefixes = [p for k in fam_keys for p in familia_map.get(k, [])]

    scored = []
    for base_norm, url in img_index.items():
        bonus = 1.0 if (host_tok and host_tok in base_norm) else 0.0
        base_tokens = set(re.split(r"[-_.]+", base_norm))
        inter = token_set & base_tokens
        union = token_set | base_tokens if token_set or base_tokens else {"_"}
        jacc = len(inter) / max(1, len(union))
        ratio = difflib.SequenceMatcher(None, t_norm, base_norm).ratio()
        path_hit = 1.0 if any(t in base_norm for t in path_tokens) else 0.0
        fam_bonus = 1.0 if any(pref in base_norm for pref in fam_prefixes) else 0.0
        score = (0.5 * bonus) + (0.3 * jacc) + (0.2 * ratio) + (0.10 * path_hit) + (0.15 * fam_bonus)

        scored.append((base_norm, url, score, jacc, ratio, bonus, path_hit, fam_bonus))

    scored.sort(key=lambda x: x[2], reverse=True)
    return [
        {
            "basename_norm": s[0],
            "url": s[1],
            "score": round(s[2], 3),
            "jaccard_tokens": round(s[3], 3),
            "ratio_difflib": round(s[4], 3),
            "bonus_dominio": s[5],
            "path_hit": s[6],
            "fam_bonus": s[7],
        }
        for s in scored[:top_k]
    ]

def audit_imagenes(limit: int = 50) -> List[Dict[str, Any]]:
    df = _get_df()
    img_index = _ensure_img_index(False)
    registros = df.fillna("").astype(str).to_dict(orient="records")

    out: List[Dict[str, Any]] = []
    for row in registros:
        if len(out) >= limit:
            break
        resolved = _best_image_for_row(row, img_index)
        if resolved:
            continue
        titulo = str(row.get(COL_TITULO, "") or row.get("Título", "") or row.get("Titulo", ""))
        enlace = str(row.get("Enlace") or row.get("URL") or row.get("URL Oficial") or "")
        candidatos = _img_candidates_for_row(row, img_index, top_k=5)
        out.append({
            "titulo": titulo,
            "enlace": enlace,
            "tipo": row.get("Tipo de recurso", ""),
            "categoria": row.get("Categoría temática", "") or row.get("Categoria tematica", ""),
            "motivo": "Sin match directo; candidatos sugeridos con scoring.",
            "candidatos": candidatos,
        })
    return out

# -------------------------
# API basada en CSV (tal cual)
# -------------------------
def get_todos_los_recursos() -> List[Dict[str, str]]:
    df = _get_df()
    img_index = _ensure_img_index()
    registros = df.fillna("").astype(str).to_dict(orient="records")

    out: List[Dict[str, str]] = []
    for row in registros:
        row["image"] = _best_image_for_row(row, img_index) or None
        out.append(row)
    return out

def get_tipos() -> List[str]:
    df = _get_df()
    return sorted(df[COL_TIPO].dropna().astype(str).str.strip().unique())

def get_resumen_por_tipo() -> List[Dict[str, Any]]:
    df = _get_df()
    col_desc = "Descripción / Uso sugerido"
    col_enlace = "Enlace"

    rows: List[Dict[str, Any]] = []
    for tipo in df[COL_TIPO].dropna().astype(str).str.strip().unique():
        slice_df = df[df[COL_TIPO].astype(str).str.strip() == tipo]
        if col_desc in slice_df.columns:
            ejemplos = slice_df[col_desc].dropna().astype(str).tolist()[:3]
        elif col_enlace in slice_df.columns:
            ejemplos = slice_df[col_enlace].dropna().astype(str).tolist()[:3]
        else:
            ejemplos = []
        descripcion = (
            f"Contiene recursos como: {', '.join(ejemplos)}"
            if ejemplos else "Contiene múltiples recursos de esta categoría."
        )
        rows.append({
            "tipo": tipo,
            "descripcion": descripcion,
            "total": int(len(slice_df)),
            "ejemplos": ejemplos,
        })
    rows.sort(key=lambda x: x["total"], reverse=True)
    return rows

def get_detalle_por_tipo(tipo: str) -> Dict[str, Any]:
    df = _get_df()
    df_aux = df.copy()
    df_aux[COL_TIPO] = df_aux[COL_TIPO].astype(str).str.strip().str.lower()
    tipo_norm = tipo.strip().lower()

    filtrado = df_aux[df_aux[COL_TIPO] == tipo_norm]
    if filtrado.empty:
        return {"tipo": tipo, "columns": [], "rows": []}

    all_cols = list(df.columns)
    table_cols = [c for c in all_cols if c != COL_TIPO]
    original_filtered = df.iloc[filtrado.index]
    rows = original_filtered[table_cols].fillna("").to_dict(orient="records")

    img_index = _ensure_img_index()
    for row in rows:
        row["image"] = _best_image_for_row(row, img_index) or None

    return {
        "tipo": original_filtered[COL_TIPO].iloc[0],
        "columns": table_cols,
        "rows": rows
    }

def get_schema() -> Dict[str, Any]:
    df = _get_df()
    return {
        "columns": list(df.columns),
        "last_fetch": _CACHE_LAST_FETCH.isoformat() if _CACHE_LAST_FETCH else None,
    }

def force_refresh():
    global _CACHE_DF, _CACHE_RAW_HASH, _CACHE_LAST_FETCH, _IMG_INDEX, _IMG_INDEX_LAST_FETCH, _CACHE_CSV_ITEMS, _CACHE_CSV_ITEMS_LAST_FETCH
    _CACHE_DF = None
    _CACHE_RAW_HASH = None
    _CACHE_LAST_FETCH = None
    _IMG_INDEX = None
    _IMG_INDEX_LAST_FETCH = None
    _CACHE_CSV_ITEMS = None
    _CACHE_CSV_ITEMS_LAST_FETCH = None

# =========================================================
# ============ NUEVO: FUSIÓN CSV + PUBLICADOS BD =========
# =========================================================

# ----- Cache de items CSV procesados -----
def _get_cached_csv_items(force: bool = False) -> List[Dict[str, Any]]:
    """Obtiene los items CSV procesados desde cache o los procesa"""
    global _CACHE_CSV_ITEMS, _CACHE_CSV_ITEMS_LAST_FETCH
    
    if (
        not force 
        and _CACHE_CSV_ITEMS is not None 
        and _CACHE_CSV_ITEMS_LAST_FETCH is not None
        and datetime.now() - _CACHE_CSV_ITEMS_LAST_FETCH < _CACHE_TTL
    ):
        return _CACHE_CSV_ITEMS
    
    # Procesar CSV
    df = _get_df(force)
    img_index = _ensure_img_index(force)
    csv_rows = df.fillna("").astype(str).to_dict(orient="records")
    csv_items = [_map_csv_row(r, img_index) for r in csv_rows]
    
    _CACHE_CSV_ITEMS = csv_items
    _CACHE_CSV_ITEMS_LAST_FETCH = datetime.now()
    return _CACHE_CSV_ITEMS

# ----- helpers de mapeo CSV -> payload público -----
def _map_csv_row(row: Dict[str, Any], img_index: Dict[str, str]) -> Dict[str, Any]:
    titulo = str(row.get(COL_TITULO, "") or row.get("Título", "") or row.get("Titulo", ""))
    enlace = str(row.get("Enlace") or row.get("URL") or row.get("URL Oficial") or "")
    data = {
        "id": None,
        "slug": _slugify_local(titulo or enlace),
        "tipo_recurso": str(row.get("Tipo de recurso") or row.get("Tipo") or ""),
        "enlace": enlace,
        "descripcion_uso": titulo,
        "categoria_tematica": str(row.get("Categoría temática") or row.get("Categoria tematica") or ""),
        "publico_objetivo": str(row.get("Público objetivo") or row.get("Publico objetivo") or ""),
        "nivel_madurez": str(row.get("Nivel de madurez") or row.get("Nivel madurez") or ""),
        "anio": str(row.get("Año") or row.get("Anio") or row.get("anio") or ""),
        "autores": str(row.get("Autor/es") or row.get("Autores") or row.get("Autor") or ""),
        "formato": str(row.get("Formato") or ""),
        "imagen_url": _best_image_for_row(row, img_index),
        # para el front: marcar fuente y una fecha razonable
        "published_at": (_CACHE_LAST_FETCH.isoformat() if _CACHE_LAST_FETCH else None),
        "source": "csv",
    }
    return data

def _filtra_busqueda(item: Dict[str, Any], q: Optional[str], tipo_recurso: Optional[str]) -> bool:
    if tipo_recurso:
        if tipo_recurso.lower() not in (item.get("tipo_recurso") or "").lower():
            return False
    if q:
        ql = q.lower()
        hay = any(
            ql in (str(item.get(f)) or "").lower()
            for f in ["descripcion_uso","categoria_tematica","autores","formato","enlace","slug","tipo_recurso"]
        )
        if not hay:
            return False
    return True

def _normaliza_clave_enlace(v: Optional[str]) -> str:
    return (v or "").strip().lower()

def _normaliza_clave_slug(v: Optional[str]) -> str:
    return (v or "").strip().lower()

# ----- lector de publicados BD -> payload público -----
def _fetch_publicados_db(db: Optional[Session]) -> List[Dict[str, Any]]:
    if db is None:
        return []
    
    try:
        B = Biblioteca
        stmt = select(B).order_by(B.published_at.desc())
        rows = list(db.execute(stmt).scalars())
    except Exception:
        return []
    
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({
            "id": r.id,
            "slug": r.slug,
            "tipo_recurso": r.tipo_recurso,
            "enlace": r.enlace,
            "descripcion_uso": r.descripcion_uso,
            "categoria_tematica": r.categoria_tematica,
            "publico_objetivo": r.publico_objetivo,
            "nivel_madurez": r.nivel_madurez,
            "anio": r.anio,
            "autores": r.autores,
            "formato": r.formato,
            "imagen_url": r.imagen_url,
            "published_at": (r.published_at.isoformat() if isinstance(r.published_at, datetime) else str(r.published_at)),
            "source": "db",
        })
    return out

# ----- API unificada: lista + detalle -----
def listar_publico_unificado(
    db: Optional[Session],
    q: Optional[str] = None,
    tipo_recurso: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Devuelve el catálogo unificado: BD (publicados) + CSV (S3).
    Reglas:
      - Se hace dedupe por ENLACE (primario) y luego por SLUG.
      - Prioridad: BD > CSV (si hay choque, gana la versión publicada).
      - Filtros (q, tipo_recurso) aplican a ambos conjuntos.
      - Orden: todos los de BD por published_at DESC, seguidos por CSV (en orden original).
    Funciona incluso si db=None (solo usa CSV).
    """
    # BD (retorna [] si db es None)
    db_items = _fetch_publicados_db(db)
    # CSV (usando cache)
    csv_items = _get_cached_csv_items()

    # Filtros
    if q or tipo_recurso:
        db_items = [x for x in db_items if _filtra_busqueda(x, q, tipo_recurso)]
        csv_items = [x for x in csv_items if _filtra_busqueda(x, q, tipo_recurso)]

    # Dedupe (prioriza DB)
    merged: List[Dict[str, Any]] = []
    seen_by_enlace: set = set()
    seen_by_slug: set = set()

    for x in db_items:
        k1 = _normaliza_clave_enlace(x.get("enlace"))
        k2 = _normaliza_clave_slug(x.get("slug"))
        if k1: seen_by_enlace.add(k1)
        if k2: seen_by_slug.add(k2)
        merged.append(x)

    for x in csv_items:
        k1 = _normaliza_clave_enlace(x.get("enlace"))
        k2 = _normaliza_clave_slug(x.get("slug"))
        if (k1 and k1 in seen_by_enlace) or (k2 and k2 in seen_by_slug):
            continue
        merged.append(x)

    # Orden: DB ya iba por fecha desc; CSV se conserva al final
    # Paginación
    total = len(merged)
    page = merged[offset: offset + limit]

    return {
        "items": page,
        "total": total,
        "limit": limit,
        "offset": offset
    }

def obtener_por_slug_unificado(db: Optional[Session], slug: str) -> Optional[Dict[str, Any]]:
    """
    Trae un ítem por slug: primero BD; si no existe, intenta resolver en CSV
    con slug calculado desde la columna título.
    Funciona incluso si db=None (solo busca en CSV).
    """
    # BD primero (si está disponible)
    row = None
    if db is not None:
        try:
            row = db.execute(select(Biblioteca).where(Biblioteca.slug == slug)).scalar_one_or_none()
        except Exception:
            row = None
    
    if row:
        return {
            "id": row.id,
            "slug": row.slug,
            "tipo_recurso": row.tipo_recurso,
            "enlace": row.enlace,
            "descripcion_uso": row.descripcion_uso,
            "categoria_tematica": row.categoria_tematica,
            "publico_objetivo": row.publico_objetivo,
            "nivel_madurez": row.nivel_madurez,
            "anio": row.anio,
            "autores": row.autores,
            "formato": row.formato,
            "imagen_url": row.imagen_url,
            "published_at": (row.published_at.isoformat() if isinstance(row.published_at, datetime) else str(row.published_at)),
            "source": "db",
        }

    # CSV fallback
    df = _get_df()
    img_index = _ensure_img_index()
    registros = df.fillna("").astype(str).to_dict(orient="records")
    for r in registros:
        titulo = str(r.get(COL_TITULO, "") or r.get("Título", "") or r.get("Titulo", "") or "")
        cand_slug = _slugify_local(titulo or (r.get("Enlace") or ""))
        if cand_slug == slug:
            mapped = _map_csv_row(r, img_index)
            return mapped
    return None
