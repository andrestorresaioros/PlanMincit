# PlanMinCIT

Backend para la gestión de procesos de planificación institucional. Expone servicios REST seguros y escalables, orientados a la integración con aplicaciones cliente y sistemas ministeriales.

## Stack

- **Framework:** FastAPI (Python 3.10+)
- **Base de datos:** PostgreSQL 14+
- **ORM y migraciones:** SQLAlchemy + Alembic
- **Validación:** Pydantic
- **Contenedores:** Docker / Docker Compose

## Estructura del repositorio

    .
    ├── backend/              # API FastAPI
    │   ├── app/
    │   │   ├── api/          # Endpoints de la API
    │   │   ├── core/         # Configuración y seguridad
    │   │   ├── models/       # Modelos de base de datos
    │   │   ├── schemas/      # Schemas Pydantic
    │   │   ├── services/     # Lógica de negocio
    │   │   └── utils/        # Utilidades
    │   ├── alembic/          # Migraciones de base de datos
    │   ├── tests/            # Tests
    │   ├── .env.example      # Ejemplo de variables de entorno
    │   ├── main.py           # Punto de entrada de la aplicación
    │   └── requirements.txt  # Dependencias
    ├── docker-compose.yml
    └── .dockerignore

## Puesta en marcha

### Con Docker

```bash
docker compose up -d --build
```

### Entorno local

```bash
cd backend

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env              # configurar variables de entorno

alembic upgrade head              # inicializar la base de datos
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

La API queda disponible en `http://localhost:8000`.

## Documentación de la API

Con la aplicación en ejecución, la documentación interactiva está disponible en:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## Más información

Detalles de instalación y ejecución del servicio en [`backend/README.md`](backend/README.md).
