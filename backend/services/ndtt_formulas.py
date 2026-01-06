"""
Módulo: ndtt_formulas.py
Define las fórmulas de cálculo de los índices intermedios NDTT,
según las fichas técnicas oficiales.
"""

import pandas as pd


# === FUNCIONES DE CÁLCULO DE ÍNDICES INTERMEDIOS ===

def calcular_IGIS(componentes: dict):
    """
    IGIS – Índice de Gobernanza e Innovación Social en Turismo
    IGIS = (PIPT + PIGT + PMA + IFFET + EPIT + GMPT + ICIEF + PCTeI + DAAT) / 9
    """
    valores = [componentes.get(k) for k in [
        "PIPT", "PIGT", "PMA", "IFFET", "EPIT", "GMPT", "ICIEF", "PCTeI", "DAAT"
    ] if componentes.get(k) is not None]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 2)


def calcular_IFFET(componentes: dict):
    """
    IFFET – Índice de Fomento Financiero y Fortalecimiento Empresarial
    IFFET = 0.20·S68 + 0.15·S6 + 0.20·S7 + 0.15·S18 + 0.30·S61
    """
    ponderaciones = {"S68": 0.20, "S6": 0.15, "S7": 0.20, "S18": 0.15, "S61": 0.30}
    valores = [componentes.get(k, 0) * w for k, w in ponderaciones.items() if componentes.get(k) is not None]
    if not valores:
        return None
    return round(sum(valores), 2)


def calcular_GAOD(componentes: dict):
    """
    GAOD – Gestión Ambiental y Ordenamiento del Destino
    GAOD = 0.20·Scons + 0.20·Sagua + 0.20·Sener + 0.20·Sres + 0.20·Scap
    """
    ponderaciones = {"Scons": 0.20, "Sagua": 0.20, "Sener": 0.20, "Sres": 0.20, "Scap": 0.20}
    valores = [componentes.get(k, 0) * w for k, w in ponderaciones.items() if componentes.get(k) is not None]
    if not valores:
        return None
    return round(sum(valores), 2)


def calcular_CDTI(componentes: dict):
    """
    CDTI – Comportamiento de la Demanda Turística Integrada
    CDTI = 0.30·RVN + 0.30·RVNR + 0.20·CVNR + 0.20·GINT
    """
    ponderaciones = {"RVN": 0.30, "RVNR": 0.30, "CVNR": 0.20, "GINT": 0.20}
    valores = [componentes.get(k, 0) * w for k, w in ponderaciones.items() if componentes.get(k) is not None]
    if not valores:
        return None
    return round(sum(valores), 2)


def calcular_DOH_TC(componentes: dict):
    """
    DOH_TC - Desempeño de la Ocupación Hotelera y Tendencia de Crecimiento
    DOH_TC = 0.50·DVN + 0.50·TCR
    """
    if componentes.get("DVN") is None and componentes.get("TCR") is None:
        return None
    d = componentes.get("DVN", 0)
    t = componentes.get("TCR", 0)
    return round((0.5 * d) + (0.5 * t), 2)
