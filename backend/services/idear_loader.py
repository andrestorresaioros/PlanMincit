# app/services/idear_loader.py
"""
Servicio para cargar y servir herramientas IDEAR desde Google Sheets.
Similar a biblioteca_loader.py pero para Google Sheets en lugar de S3.

OPTIMIZACIONES:
1. Cache de 2 horas para datos de Google Sheets
2. Pre-procesamiento y cache de items mapeados
3. Endpoint /refresh-cache para precalentar datos
"""
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path

# ===== Imports para leer publicados desde BD =====
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.idear import Idear

# Config
SHEET_ID = "1AoufhvnkZYs-2h124VIZ9CqWoOa7EhiDc7HpnXseYPY"
TAB_NAME = "Contenidos"
CREDENTIALS_FILE = Path(__file__).resolve().parent.parent.parent / "google-credentials.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# -------------------------
# Cache de Google Sheets
# -------------------------
_CACHE_SHEETS_ITEMS: Optional[List[Dict[str, Any]]] = None
_CACHE_SHEETS_LAST_FETCH: Optional[datetime] = None
_CACHE_TTL = timedelta(hours=2)

# -------------------------
# Helpers
# -------------------------
def _to_xlsx_download_url(gsheet_url: str) -> str:
    """Convierte un link de Google Sheets en link directo de descarga XLSX."""
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", gsheet_url)
    if match:
        sheet_id = match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx&id={sheet_id}"
    return gsheet_url

def _normaliza_clave_url(v: Optional[str]) -> str:
    """Normaliza URL para comparación (dedupe)"""
    return (v or "").strip().lower()

def _normaliza_clave_slug(v: Optional[str]) -> str:
    """Normaliza slug para comparación"""
    return (v or "").strip().lower()

# -------------------------
# Descarga desde Google Sheets
# -------------------------
def _fetch_from_sheets(force: bool = False) -> List[Dict[str, Any]]:
    """Lee datos de Google Sheets con cache"""
    global _CACHE_SHEETS_ITEMS, _CACHE_SHEETS_LAST_FETCH
    
    if (
        not force 
        and _CACHE_SHEETS_ITEMS is not None 
        and _CACHE_SHEETS_LAST_FETCH is not None
        and datetime.now() - _CACHE_SHEETS_LAST_FETCH < _CACHE_TTL
    ):
        return _CACHE_SHEETS_ITEMS

    try:
        creds = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(TAB_NAME)
        rows = sheet.get_all_records(head=2)  # Fila 2 como headers
        
        items = []
        for i, row in enumerate(rows, start=1):
            items.append({
                "id": str(i),
                "title": row.get("Nombre de la herramienta", ""),
                "description": row.get("Descripción breve", ""),
                "image": "https://api.builder.io/api/v1/image/assets/TEMP/placeholder?width=240",
                "paquete": row.get("Paquete", ""),
                "publico": row.get("Público Objetivo", ""),
                "subfase": row.get("SUBFASE DE IDEAR", ""),
                "objetivo": row.get("OBJETIVO", ""),
                "nivel": row.get("Nivel de Madurez", ""),
                "detailUrl": _to_xlsx_download_url(row.get("URL", "")),
                "hasButton": bool(row.get("URL")),
                "url_raw": row.get("URL", ""),  # Para dedupe
            })
        
        _CACHE_SHEETS_ITEMS = items
        _CACHE_SHEETS_LAST_FETCH = datetime.now()
        return items
    
    except Exception as e:
        print(f"Error al cargar desde Google Sheets: {e}")
        # Si hay cache viejo, usarlo
        if _CACHE_SHEETS_ITEMS is not None:
            return _CACHE_SHEETS_ITEMS
        return []

# -------------------------
# Mapeo de row Sheets -> payload unificado
# -------------------------
def _map_sheets_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Mapea row de Sheets al formato que espera el frontend"""
    return {
        "id": row.get("id"),
        "title": row.get("title") or "",
        "description": row.get("description") or "",
        "image": row.get("image") or "",
        "paquete": row.get("paquete") or "",
        "publico": row.get("publico") or "",
        "subfase": row.get("subfase") or "",
        "objetivo": row.get("objetivo") or "",
        "nivel": row.get("nivel") or "",
        "detailUrl": row.get("detailUrl") or "",
        "hasButton": row.get("hasButton", False),
        "url_raw": row.get("url_raw") or "",
        "source": "sheets",  # Marcador de origen
    }

# -------------------------
# Lectura de publicados BD -> payload unificado
# -------------------------
def _fetch_publicados_db(db: Optional[Session]) -> List[Dict[str, Any]]:
    """Lee herramientas publicadas en BD y las mapea al formato del frontend"""
    if db is None:
        return []
    
    try:
        stmt = select(Idear).order_by(Idear.published_at.desc())
        items = list(db.execute(stmt).scalars())
    except Exception:
        return []
    
    result = []
    for item in items:
        result.append({
            "id": f"db-{item.id}",
            "title": item.nombre_herramienta or "",
            "description": item.descripcion_breve or "",
            "image": item.imagen_url or "https://api.builder.io/api/v1/image/assets/TEMP/placeholder?width=240",
            "paquete": item.paquete or "",
            "publico": item.publico_objetivo or "",
            "subfase": item.subfase or "",
            "objetivo": item.objetivo or "",
            "nivel": item.nivel_madurez or "",
            "detailUrl": item.url or "",
            "hasButton": bool(item.url),
            "url_raw": item.url or "",
            "slug": item.slug,
            "source": "db",  # Marcador de origen
        })
    
    return result

# -------------------------
# Helpers de filtrado
# -------------------------
def _filtra_busqueda(item: Dict[str, Any], paquete: Optional[str], publico: Optional[str], subfase: Optional[str]) -> bool:
    """Filtra por paquete, público, subfase (match parcial case-insensitive)"""
    if paquete:
        if not item.get("paquete") or paquete.lower() not in item["paquete"].lower():
            return False
    if publico:
        if not item.get("publico") or publico.lower() not in item["publico"].lower():
            return False
    if subfase:
        if not item.get("subfase") or subfase.lower() not in item["subfase"].lower():
            return False
    return True

# -------------------------
# API unificada: lista
# -------------------------
def listar_publico_unificado(
    db: Optional[Session],
    paquete: Optional[str] = None,
    publico: Optional[str] = None,
    subfase: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fusiona herramientas de:
    1. BD (publicados) - si está disponible
    2. Google Sheets - fallback
    
    Dedupe por URL.
    Retorna: { tools, filters }
    """
    # 1. Leer BD (retorna [] si db es None)
    bd_items = _fetch_publicados_db(db)
    
    # 2. Leer Sheets (con cache)
    sheets_items_raw = _fetch_from_sheets(force=False)
    sheets_items = [_map_sheets_row(r) for r in sheets_items_raw]
    
    # 3. Fusión + dedupe por URL
    all_items = []
    seen_urls = set()
    
    # Prioridad: BD primero (más confiable)
    for item in bd_items + sheets_items:
        url_key = _normaliza_clave_url(item.get("url_raw") or item.get("detailUrl"))
        if url_key and url_key in seen_urls:
            continue
        if url_key:
            seen_urls.add(url_key)
        all_items.append(item)
    
    # 4. Filtrar
    filtered = [
        item for item in all_items
        if _filtra_busqueda(item, paquete, publico, subfase)
    ]
    
    # 5. Construir filtros únicos
    paquetes_set = set()
    publicos_set = set()
    subfases_set = set()
    
    for item in all_items:  # Usar todos los items para los filtros, no solo filtrados
        if item.get("paquete"):
            paquetes_set.add(item["paquete"])
        if item.get("publico"):
            publicos_set.add(item["publico"])
        if item.get("subfase"):
            subfases_set.add(item["subfase"])
    
    filters_payload = {
        "paquetes": sorted(paquetes_set),
        "publicos": sorted(publicos_set),
        "subfases": sorted(subfases_set),
    }
    
    return {
        "tools": filtered,
        "filters": filters_payload,
    }

# -------------------------
# API unificada: detalle por slug
# -------------------------
def obtener_por_slug_unificado(db: Optional[Session], slug: str) -> Optional[Dict[str, Any]]:
    """
    Busca herramienta por slug en BD.
    (Google Sheets no tiene slugs, así que solo BD)
    Retorna None si la BD no está disponible.
    """
    if db is None:
        return None
    
    try:
        obj = db.scalar(select(Idear).where(Idear.slug == slug))
    except Exception:
        return None
    
    if not obj:
        return None
    
    return {
        "id": f"db-{obj.id}",
        "title": obj.nombre_herramienta or "",
        "description": obj.descripcion_breve or "",
        "image": obj.imagen_url or "",
        "paquete": obj.paquete or "",
        "publico": obj.publico_objetivo or "",
        "subfase": obj.subfase or "",
        "objetivo": obj.objetivo or "",
        "nivel": obj.nivel_madurez or "",
        "detailUrl": obj.url or "",
        "hasButton": bool(obj.url),
        "slug": obj.slug,
        "source": "db",
    }

# -------------------------
# Forzar refresh de cache
# -------------------------
def force_refresh():
    """Fuerza recarga de cache desde Google Sheets"""
    global _CACHE_SHEETS_ITEMS, _CACHE_SHEETS_LAST_FETCH
    _CACHE_SHEETS_ITEMS = None
    _CACHE_SHEETS_LAST_FETCH = None
    _fetch_from_sheets(force=True)
