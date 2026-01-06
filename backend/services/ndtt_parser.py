import os
import json
import pandas as pd
from datetime import datetime

# === CONFIGURACIÓN ===
INPUT_DIR = "app/data/ndtt_raw"
OUTPUT_FILE = "app/data/indicadores_ndtt.csv"
LOG_FILE = "app/logs/ndtt_parser.log"

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def log_message(msg: str):
    """Guarda un mensaje con timestamp en el log."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    print(msg)


def parse_ndtt_json(filepath: str):
    """Parsea un archivo JSON NDTT de un municipio a filas planas (seguro contra datos inválidos)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log_message(f"⚠️ No se pudo leer {filepath}: {e}")
        return []

    # Validación de estructura
    if not isinstance(data, dict) or "data" not in data or not isinstance(data["data"], list) or len(data["data"]) == 0:
        log_message(f"⚠️ Estructura inválida en {filepath}: tipo {type(data).__name__}")
        return []

    entry = data["data"][0]
    if not isinstance(entry, dict):
        log_message(f"⚠️ Entrada inválida en {filepath}: tipo {type(entry).__name__}")
        return []

    cod_mun = entry.get("cod_municipio", "SIN_CODIGO")
    nom_mun = entry.get("nombre_municipio", "SIN_NOMBRE")
    url_pdf = entry.get("url_pdfinforme", None)
    respuesta = entry.get("respuesta", [])

    if not isinstance(respuesta, list) or len(respuesta) == 0:
        log_message(f"⚠️ Municipio {cod_mun} sin 'respuesta'. Saltando...")
        return []

    rows = []

    for bloque in respuesta:
        for tipo in ["oferta", "demanda"]:
            if tipo not in bloque:
                continue

            for eje_item in bloque[tipo]:
                eje_nombre = None
                for key in eje_item.keys():
                    if key.startswith("eje"):
                        eje_nombre = eje_item[key]
                        break
                if not eje_nombre:
                    eje_nombre = "SIN_EJE"

                criterios = eje_item.get("criterios", [])
                if not isinstance(criterios, list):
                    continue

                for criterio in criterios:
                    if not isinstance(criterio, dict):
                        continue
                    nombre_criterio = criterio.get("nombre_criterio")
                    puntaje = criterio.get("puntaje_criterio", 0)

                    # Documentos
                    for doc in criterio.get("criterios_documentos", []):
                        if not isinstance(doc, dict):
                            continue
                        rows.append({
                            "cod_municipio": cod_mun,
                            "nombre_municipio": nom_mun,
                            "tipo": tipo,
                            "eje": eje_nombre,
                            "nombre_criterio": nombre_criterio,
                            "puntaje_criterio": puntaje,
                            "nombre_cifra": None,
                            "valor_cifra": None,
                            "url_documento": doc.get("urlfiledoc"),
                            "detalle_documento": doc.get("nombre"),
                            "url_pdfinforme": url_pdf
                        })

                    # Cifras
                    for cifra in criterio.get("criterios_cifras", []):
                        if not isinstance(cifra, dict):
                            continue
                        nombre_cifra = cifra.get("nombre_cifra")
                        valor_cifra = cifra.get("valor_cifra")

                        if isinstance(valor_cifra, list):
                            for v in valor_cifra:
                                rows.append({
                                    "cod_municipio": cod_mun,
                                    "nombre_municipio": nom_mun,
                                    "tipo": tipo,
                                    "eje": eje_nombre,
                                    "nombre_criterio": nombre_criterio,
                                    "puntaje_criterio": puntaje,
                                    "nombre_cifra": nombre_cifra,
                                    "valor_cifra": json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v,
                                    "url_documento": None,
                                    "detalle_documento": None,
                                    "url_pdfinforme": url_pdf
                                })
                        else:
                            rows.append({
                                "cod_municipio": cod_mun,
                                "nombre_municipio": nom_mun,
                                "tipo": tipo,
                                "eje": eje_nombre,
                                "nombre_criterio": nombre_criterio,
                                "puntaje_criterio": puntaje,
                                "nombre_cifra": nombre_cifra,
                                "valor_cifra": valor_cifra,
                                "url_documento": None,
                                "detalle_documento": None,
                                "url_pdfinforme": url_pdf
                            })

    return rows

def build_csv():
    """Construye el dataset consolidado de todos los municipios."""
    all_rows = []
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".json")]
    log_message(f"📊 Iniciando parsing de {len(files)} archivos NDTT...")

    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)
        log_message(f"Procesando {filename}...")
        try:
            rows = parse_ndtt_json(filepath)
            all_rows.extend(rows)
            log_message(f"✅ {filename}: {len(rows)} registros extraídos.")
        except Exception as e:
            log_message(f"❌ Error procesando {filename}: {e}")

    if not all_rows:
        log_message("⚠️ No se generaron filas. Verifica los archivos fuente.")
        return

    df = pd.DataFrame(all_rows)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    log_message(f"✅ Dataset consolidado guardado en {OUTPUT_FILE} ({len(df)} filas).")


if __name__ == "__main__":
    build_csv()
