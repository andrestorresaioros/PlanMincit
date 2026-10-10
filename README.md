# PlanMinCIT

![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL_15-4169E1?style=flat&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![Estado](https://img.shields.io/badge/estado-finalizado-lightgrey?style=flat)

Backend para la gestión de procesos de planificación institucional, diseñado para exponer servicios REST que consuman aplicaciones cliente.

> **Estado del proyecto:** finalizado. Este repositorio conserva la infraestructura del servicio —contenedores, dependencias fijadas y configuración de entorno—; el código fuente de la API no forma parte de él.

## Stack

| Capa | Tecnología |
|---|---|
| Framework | FastAPI + Uvicorn |
| Validación y configuración | Pydantic v2, pydantic-settings, python-dotenv |
| Persistencia | PostgreSQL 15, SQLAlchemy 2, Alembic |
| Seguridad | JWT (python-jose), hash de contraseñas con passlib/bcrypt |
| Contenedores | Docker y Docker Compose |

## Contenido

```
.
├── backend/
│   ├── Dockerfile         # Imagen Python 3.11 para la API
│   ├── requirements.txt   # Dependencias fijadas
│   ├── .env.example       # Variables de entorno de la API
│   └── README.md          # Guía del servicio y estructura de la API
├── docker-compose.yml     # PostgreSQL + API con recarga en caliente
└── .dockerignore
```

## Configuración

Variables de la API (`backend/.env`, a partir de [`backend/.env.example`](backend/.env.example)):

| Variable | Uso |
|---|---|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL |
| `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Firma y vigencia de los tokens JWT |
| `ALLOWED_ORIGINS` | Orígenes permitidos por CORS |
| `APP_NAME`, `DEBUG`, `ENVIRONMENT` | Parámetros generales |

Docker Compose admite además `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` y `POSTGRES_HOST_PORT`; si no se definen, usa valores de desarrollo.

## Uso de la configuración

La base de datos del proyecto puede levantarse de forma independiente con Docker Compose:

```bash
docker compose up -d db
```

PostgreSQL queda disponible en `localhost:5432` con las credenciales de desarrollo definidas en `docker-compose.yml`. La API se documentaba con Swagger UI (`/docs`) y ReDoc (`/redoc`), generados automáticamente por FastAPI.

## Autor

**César Andrés Torres Bernal** · [GitHub](https://github.com/andrestorresaioros) · [LinkedIn](https://www.linkedin.com/in/andr%C3%A9s-torres10)

## Licencia

Distribuido bajo la licencia MIT. Consulta [LICENSE](LICENSE).
