import os, json, csv
from datetime import datetime

RAW_PATH = "app/data/ndtt_raw/"
REPORT_PATH = "app/reports/reporte_diagnostico_ndtt.csv"
LOG_PATH = "app/logs/ndtt_report.log"

os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


def log(msg):
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


def analizar_ndtt():
    total = len(os.listdir(RAW_PATH))
    con_respuesta = 0
    con_criterios = 0
    vacios = 0
    resultados = []

    log(f"🚀 Iniciando análisis NDTT de {total} municipios...")

    for filename in sorted(os.listdir(RAW_PATH)):
        file_path = os.path.join(RAW_PATH, filename)
        cod = filename.replace(".json", "")

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            municipio = data.get("data", [{}])[0].get("nombre_municipio", "Desconocido")

            if data.get("data") and len(data["data"]) > 0:
                item = data["data"][0]
                respuesta = item.get("respuesta", [])
                if respuesta:
                    con_respuesta += 1
                    # Verificamos oferta o demanda con criterios
                    r = respuesta[0]
                    tiene_criterios = False
                    for bloque in ["oferta", "demanda"]:
                        if bloque in r and isinstance(r[bloque], list):
                            for eje in r[bloque]:
                                if eje.get("criterios"):
                                    tiene_criterios = True
                                    break
                    if tiene_criterios:
                        con_criterios += 1
                        estado = "✅ Con criterios válidos"
                    else:
                        estado = "⚠️ Sin criterios"
                else:
                    estado = "⚠️ Sin respuesta"
                    vacios += 1
            else:
                estado = "❌ Sin data"
                vacios += 1

            resultados.append({
                "cod_municipio": cod,
                "nombre_municipio": municipio,
                "estado": estado
            })

        except Exception as e:
            log(f"❌ Error leyendo {filename}: {e}")
            resultados.append({
                "cod_municipio": cod,
                "nombre_municipio": "Desconocido",
                "estado": f"❌ Error: {str(e)[:80]}"
            })

    # Guardar CSV resumen
    with open(REPORT_PATH, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["cod_municipio", "nombre_municipio", "estado"])
        writer.writeheader()
        writer.writerows(resultados)

    log("─────────────────────────────────────────────")
    log(f"Total municipios analizados: {total}")
    log(f"Con respuesta NDTT: {con_respuesta}")
    log(f"Con criterios válidos: {con_criterios}")
    log(f"Sin información o vacíos: {vacios}")
    log("─────────────────────────────────────────────")
    log(f"📄 Reporte detallado guardado en {REPORT_PATH}")


if __name__ == "__main__":
    analizar_ndtt()
