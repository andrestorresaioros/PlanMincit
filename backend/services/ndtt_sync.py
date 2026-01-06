import os
import json
import time
import requests
from datetime import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.data_sources.diccionario_municipios import municipios_data

# === CONFIGURACIÓN ===
LOGIN_URL = "https://ndtt.mincit.gov.co/api/login"
DATA_URL = "https://ndtt.mincit.gov.co/api/info-municipio"

EMAIL = "turismo40@gmail.com"
PASSWORD = "Abcd$1234"

OUTPUT_DIR = "app/data/ndtt_raw"
LOG_FILE = "app/logs/ndtt_sync.log"

MAX_WORKERS = 5             # Número de descargas simultáneas
DELAY_BETWEEN_BATCHES = 3   # Delay entre grupos de requests (segundos)
DELAY_ON_ERROR = 5          # Delay tras error leve
DELAY_ON_429 = 20           # Delay cuando NDTT devuelve Too Many Requests
DELAY_ON_401 = 10           # Delay tras renovar token

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def log_message(msg: str):
    """Registra mensajes en archivo y consola."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    print(msg)


def get_auth_token():
    """Obtiene un nuevo token de autenticación NDTT."""
    try:
        resp = requests.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD}, timeout=20)
        if resp.status_code != 200:
            raise Exception(f"Error {resp.status_code} en login")
        token = resp.json().get("token") or resp.json().get("access_token")
        if not token:
            raise Exception("No se recibió token en la respuesta del login")
        log_message("🔐 Token de autenticación obtenido correctamente.")
        return token
    except Exception as e:
        log_message(f"❌ Error en autenticación: {e}")
        return None


def fetch_municipio_data(codmun: str, token: str, retries: int = 3):
    """Descarga los datos de un municipio con control de errores 401 y 429."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    params = {"codmun": codmun}

    for attempt in range(retries):
        try:
            response = requests.get(DATA_URL, headers=headers, params=params, timeout=60)
            if response.status_code == 200:
                return response.json()

            elif response.status_code == 429:
                wait_time = (attempt + 1) * DELAY_ON_429
                log_message(f"⚠️ 429 Too Many Requests para {codmun}. Esperando {wait_time}s...")
                time.sleep(wait_time)
                continue

            elif response.status_code == 401:
                log_message("🔁 Token expirado, renovando...")
                new_token = get_auth_token()
                if not new_token:
                    log_message("❌ Fallo al renovar token.")
                    return None
                headers["Authorization"] = f"Bearer {new_token}"
                time.sleep(DELAY_ON_401)
                continue

            else:
                log_message(f"⚠️ Error {response.status_code} para {codmun}: {response.text[:150]}")
                time.sleep(DELAY_ON_ERROR)
                return None

        except Exception as e:
            log_message(f"❌ Error al consultar {codmun}: {e}")
            time.sleep(DELAY_ON_ERROR)

    log_message(f"❌ Fallo definitivo al consultar {codmun} tras {retries} intentos.")
    return None


def save_json(codmun: str, data: dict):
    """Guarda el JSON del municipio."""
    file_path = os.path.join(OUTPUT_DIR, f"{codmun}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def process_municipio(codmun: str, token: str):
    """Procesa un municipio completo: descarga y guarda su JSON."""
    mun_info = municipios_data.get(codmun, {})
    nombre = mun_info.get("municipio", "SIN_NOMBRE")
    dep = mun_info.get("departamento", "SIN_DEP")

    file_path = os.path.join(OUTPUT_DIR, f"{codmun}.json")
    if os.path.exists(file_path):
        return f"⏩ {nombre} ({dep}) ya descargado."

    data = fetch_municipio_data(codmun, token)
    if data:
        save_json(codmun, data)
        return f"✅ {nombre} ({dep}) descargado correctamente."
    else:
        return f"❌ {nombre} ({dep}) falló."


def sync_all(start_from: str = None, limit: int = None):
    """Sincroniza los municipios NDTT con descarga paralela segura."""
    token = get_auth_token()
    if not token:
        log_message("❌ No se pudo obtener token. Cancelando sincronización.")
        return

    codigos = sorted(municipios_data.keys())
    if start_from and start_from in codigos:
        codigos = codigos[codigos.index(start_from):]
    if limit:
        codigos = codigos[:limit]

    total = len(codigos)
    log_message(f"🚀 Iniciando sincronización NDTT para {total} municipios (máx {MAX_WORKERS} hilos).")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_municipio, cod, token): cod for cod in codigos}

        for i, future in enumerate(tqdm(as_completed(futures), total=total, desc="Descargando municipios", ncols=100)):
            codmun = futures[future]
            try:
                result = future.result()
                tqdm.write(result)
            except Exception as e:
                tqdm.write(f"⚠️ {codmun}: {e}")

            # Delay global entre lotes para no saturar API
            if i % MAX_WORKERS == 0:
                time.sleep(DELAY_BETWEEN_BATCHES)

    log_message("🏁 Sincronización completada.")


if __name__ == "__main__":
    # Puedes cambiar estos valores para pruebas
    # sync_all(start_from=None, limit=20)  # 20 municipios para test
    sync_all()
