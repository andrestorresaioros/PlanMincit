"""
Módulo: ndtt_indices.py
Define la composición de los 4 índices finales del NDTT
y combina los subíndices calculados en ndtt_formulas.py.
"""

from statistics import mean


def calcular_indices_finales(subindices: dict):
    """
    Calcula los 4 índices globales NDTT a partir de los subíndices disponibles.
    Cada subíndice se normaliza en 0–100.
    """
    resultados = {}

    # 1. Gobernanza e Innovación
    componentes_gob = [
        subindices.get("IGIS"),
        subindices.get("IFFET"),
        subindices.get("PMA"),
        subindices.get("ICIEF"),
        subindices.get("EPIT"),
        subindices.get("GMPT"),
    ]
    resultados["Gobernanza e Innovación"] = round(mean([v for v in componentes_gob if v is not None]), 2) if any(componentes_gob) else None

    # 2. Sostenibilidad
    componentes_sost = [
        subindices.get("GAOD"),
        subindices.get("GALAC"),
        subindices.get("ICRD"),
    ]
    resultados["Sostenibilidad"] = round(mean([v for v in componentes_sost if v is not None]), 2) if any(componentes_sost) else None

    # 3. Competitividad / Calidad
    componentes_comp = [
        subindices.get("CDTI"),
        subindices.get("DOH_TC"),
    ]
    resultados["Competitividad y Calidad"] = round(mean([v for v in componentes_comp if v is not None]), 2) if any(componentes_comp) else None

    # 4. Demanda Turística
    componentes_dem = [
        subindices.get("CDTI"),
        subindices.get("DOH_TC"),
    ]
    resultados["Demanda Turística"] = round(mean([v for v in componentes_dem if v is not None]), 2) if any(componentes_dem) else None

    # Índice NDTT Total
    valores_finales = [v for v in resultados.values() if v is not None]
    resultados["NDTT_Total"] = round(mean(valores_finales), 2) if valores_finales else None

    return resultados
