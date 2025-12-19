# PlanMinCIT Backend

API backend desarrollada con FastAPI para el proyecto PlanMinCIT.

## Requisitos

- Python 3.10+
- PostgreSQL 14+

## Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate  # En Windows
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

4. Inicializar la base de datos:
```bash
alembic upgrade head
```

## Ejecución

### Desarrollo
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Producción
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Documentación API

Una vez ejecutada la aplicación, la documentación interactiva está disponible en:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Estructura del Proyecto

```
backend/
├── app/
│   ├── api/          # Endpoints de la API
│   ├── core/         # Configuración y seguridad
│   ├── models/       # Modelos de base de datos
│   ├── schemas/      # Schemas Pydantic
│   ├── services/     # Lógica de negocio
│   └── utils/        # Utilidades
├── alembic/          # Migraciones de base de datos
├── tests/            # Tests
├── .env.example      # Ejemplo de variables de entorno
├── main.py           # Punto de entrada de la aplicación
└── requirements.txt  # Dependencias
```
