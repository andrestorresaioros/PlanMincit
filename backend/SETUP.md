# 🚀 Setup Rápido - PlanMinCIT Backend

## Pasos para inicializar el proyecto

### 1. Crear la base de datos PostgreSQL

```bash
# Conectar a PostgreSQL como superusuario
sudo -u postgres psql

# Dentro de psql, ejecutar:
CREATE DATABASE planmincit;
CREATE USER planmincit_user WITH PASSWORD 'tu_password_seguro';
GRANT ALL PRIVILEGES ON DATABASE planmincit TO planmincit_user;
\q
```

### 2. Configurar el entorno

```bash
# Crear archivo .env
cp .env.example .env

# Editar .env y configurar:
# - DATABASE_URL con tus credenciales de PostgreSQL
# - SECRET_KEY (genera uno nuevo con: openssl rand -hex 32)
# - ADMIN_EMAIL y ADMIN_PASSWORD
```

### 3. Instalar dependencias

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 4. Crear las tablas con Alembic

```bash
# Generar migración inicial
alembic revision --autogenerate -m "Initial migration"

# Aplicar migración
alembic upgrade head
```

### 5. Ejecutar seed de datos iniciales

```bash
python scripts/seed.py
```

Esto creará:
- Los 3 instrumentos (RURAL, URBANO, REGION)
- El usuario administrador

### 6. Ejecutar la aplicación

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Acceder a la documentación

Abre en tu navegador:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🧪 Probar la API

### Login como admin

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@planmincit.gov.co",
    "password": "Admin123!Change"
  }'
```

### Crear una autoridad turística

```bash
curl -X POST http://localhost:8000/admin/authorities \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN" \
  -d '{
    "email": "municipio@test.com",
    "password": "Password123!",
    "authority_type": "MUNICIPIO",
    "display_name": "Municipio de Cartagena",
    "instrument_assignments": [
      {"instrument_code": "RURAL", "role": "LEADER_PLANNING"},
      {"instrument_code": "URBANO", "role": "STRATEGIC_ALLY"},
      {"instrument_code": "REGION", "role": "STRATEGIC_ALLY"}
    ]
  }'
```

---

## 🧪 Ejecutar tests

```bash
pytest tests/ -v
```

---

## 📝 Comandos útiles

```bash
# Ver migraciones aplicadas
alembic current

# Revertir última migración
alembic downgrade -1

# Ver historial de migraciones
alembic history

# Crear nueva migración
alembic revision --autogenerate -m "Descripción del cambio"

# Aplicar todas las migraciones
alembic upgrade head
```
