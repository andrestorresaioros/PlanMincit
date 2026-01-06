import pandas as pd
import os
from datetime import datetime

# === Imports existentes ===
from app.services.ndtt_formulas import (
    calcular_IFFET,
    calcular_GAOD,
    calcular_CDTI,
    calcular_DOH_TC
)
from app.services.ndtt_indices import calcular_indices_finales

# === Nuevo import para obtener los departamentos ===
from app.data_sources.diccionario_municipios import municipios_data

# === Configuración de rutas ===
INPUT_FILE = "app/data/indicadores_ndtt.csv"
OUTPUT_FILE = "app/data/indicadores_calculados.csv"
LOG_FILE = "app/logs/ndtt_calculator.log"

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# === Mapeo de municipios → departamentos ===
departamentos_map = {
    str(codigo).zfill(5): datos["departamento"]
    for codigo, datos in municipios_data.items()
    if isinstance(datos, dict) and "departamento" in datos
}


def log_message(msg: str):
    """Guarda mensajes con timestamp en el log."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    print(msg)


# === FUNCIONES BASE DE CÁLCULO ===

def calcular_IGIS(df_mun):
    criterios_igis = [
        "El turismo en el Plan de Ordenamiento Territorial",
        "Turismo en el Plan de Desarrollo Distrital o Municipal",
        "Plan de Desarrollo Turístico u otro instrumento de planificación turística",
        "Plan de acción de turismo sostenible",
        "Lineamientos de accesibilidad para el sector turístico",
        "Turismo y la Gestión del Riesgo",
        "Plan de mercadeo y promoción"
    ]
    subset = df_mun[df_mun["nombre_criterio"].isin(criterios_igis)]
    if subset.empty:
        return None
    return round((subset["puntaje_criterio"].mean() / 10) * 100, 2)


def calcular_PIGT(df_mun):
    criterios_pigt = [
        "Consejo distrital o municipal de turismo",
        "Articulación del municipio con entidades del orden nacional y departamental que lideran y/o gestionan el turismo.",
        "Oficina para la gestión del turismo"
    ]
    subset = df_mun[df_mun["nombre_criterio"].isin(criterios_pigt)]
    if subset.empty:
        return None
    return round((subset["puntaje_criterio"].mean() / 10) * 100, 2)


def calcular_PMA(df_mun):
    criterios_pma = [
        "Articulación del municipio con entidades del orden nacional y departamental que lideran y/o gestionan el turismo.",
        "Consejo distrital o municipal de turismo",
        "Vinculación a la estrategia Gestión Integral de Destinos o la estrategia Territorios Turísticos de Paz"
    ]
    subset = df_mun[df_mun["nombre_criterio"].isin(criterios_pma)]
    if subset.empty:
        return None
    return round((subset["puntaje_criterio"].mean() / 10) * 100, 2)


def calcular_GPPD(df_mun):
    criterios_gppd = [
        "Plan de mercadeo y promoción",
        "Presencia digital nacional del distrito o municipio en la plataforma Google Trends.",
        "Presencia digital mundial del distrito o municipio en la plataforma Google Trends."
    ]
    subset = df_mun[df_mun["nombre_criterio"].isin(criterios_gppd)]
    if subset.empty:
        return None
    return round((subset["puntaje_criterio"].mean() / 10) * 100, 2)


# === PROCESAMIENTO PRINCIPAL ===

def calcular_indicadores():
    if not os.path.exists(INPUT_FILE):
        log_message(f"❌ No se encontró el archivo {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    required_columns = {"cod_municipio", "nombre_municipio", "nombre_criterio", "puntaje_criterio"}
    if not required_columns.issubset(df.columns):
        log_message("❌ Las columnas esperadas no existen en el archivo CSV.")
        log_message(f"Columnas disponibles: {list(df.columns)}")
        return

    municipios = df["cod_municipio"].unique()
    resultados = []

    log_message(f"📊 Iniciando cálculo de indicadores para {len(municipios)} municipios...")

    for cod in municipios:
        df_mun = df[df["cod_municipio"] == cod]
        nombre = df_mun["nombre_municipio"].iloc[0] if not df_mun.empty else "Desconocido"
        departamento = departamentos_map.get(str(cod).zfill(5), "Desconocido")

        # Subíndices base (mezcla de funciones internas y externas)
        subindices = {
            "IGIS": calcular_IGIS(df_mun),
            "IFFET": calcular_IFFET(df_mun),
            "GAOD": calcular_GAOD(df_mun),
            "CDTI": calcular_CDTI(df_mun),
            "DOH_TC": calcular_DOH_TC(df_mun),
            "PMA": calcular_PMA(df_mun),
            "PIGT": calcular_PIGT(df_mun),
            "GPPD": calcular_GPPD(df_mun),
        }

        # Índices finales (desde ndtt_indices.py)
        indices_finales = calcular_indices_finales(subindices)

        # Consolidación total
        resultados.append({
            "cod_municipio": cod,
            "nombre_municipio": nombre,
            "departamento": departamento,
            "ubicacion_departamento": f"{departamento}, Colombia",  # 👈 NUEVA COLUMNA
            **subindices,
            **indices_finales
        })

    # Exportación
    df_out = pd.DataFrame(resultados)
    df_out.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    log_message("────────────────────────────────────────────")
    log_message(f"✅ Indicadores calculados guardados en {OUTPUT_FILE}")
    log_message(f"📈 Total municipios procesados: {len(resultados)}")
    log_message(f"📁 Columnas exportadas: {list(df_out.columns)}")
    log_message("────────────────────────────────────────────")
    log_message(df_out.head().to_string(index=False))


if __name__ == "__main__":
    calcular_indicadores()
