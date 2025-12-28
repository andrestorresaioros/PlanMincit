# PlanMinCIT Backend - Sistema de Planificación Turística

API backend desarrollada con **FastAPI** para la gestión de planificación turística del Ministerio de Comercio, Industria y Turismo (MinCIT).

## 🎯 Características

- **Autenticación JWT** con tokens de acceso y refresco
- **RBAC (Role-Based Access Control)** con 3 roles:
  - Usuario público (sin autenticación)
  - Autoridad Turística (MUNICIPIO/DEPARTAMENTO/REGION/INDEPENDIENTE)
  - Administrador
- **Gestión de instrumentos** de planificación (RURAL, URBANO, REGION)
- **Control de roles por instrumento**: Líder de Planificación y Aliado Estratégico
- **Gestión de documentos** con permisos basados en roles
- **Validaciones de negocio**:
  - 1 líder máximo por instrumento
  - 8 aliados máximo por instrumento
  - 3 instrumentos por autoridad

## 📋 Requisitos

- Python 3.10+
- PostgreSQL 14+

## 🚀 Instalación

### 1. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate  # En Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar base de datos PostgreSQL

Crear la base de datos:

```bash
# Conectar a PostgreSQL
psql -U postgres

# Crear base de datos
CREATE DATABASE planmincit;

# Salir
\q
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con tus configuraciones:

```env
DATABASE_URL=postgresql://postgres:tu_password@localhost:5432/planmincit
SECRET_KEY=genera-un-secret-key-seguro-aqui
ADMIN_EMAIL=admin@planmincit.gov.co
ADMIN_PASSWORD=CambiaEstaContraseña123!
```

Para generar un SECRET_KEY seguro:

```bash
openssl rand -hex 32
```

### 5. Ejecutar migraciones de base de datos

```bash
alembic upgrade head
```

### 6. Ejecutar seed inicial (instrumentos y admin)

```bash
python scripts/seed.py
```

Esto creará:
- Los 3 instrumentos (RURAL, URBANO, REGION)
- El usuario administrador con las credenciales del `.env`

## 🏃 Ejecución

### Desarrollo

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Producción

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📚 Documentación API

Una vez ejecutada la aplicación, la documentación interactiva está disponible en:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Tests

Ejecutar tests:

```bash
pytest tests/ -v
```

Tests con cobertura:

```bash
pytest tests/ -v --cov=app --cov-report=html
```

## 📁 Estructura del proyecto

```
backend/
├── app/
│   ├── api/
│   │   ├── dependencies/    # Dependencias de autenticación y autorización
│   │   └── routers/         # Endpoints (public, auth, admin, authority)
│   ├── core/
│   │   ├── config.py        # Configuración de la aplicación
│   │   └── security.py      # JWT, hashing de passwords
│   ├── db/
│   │   └── session.py       # Configuración de SQLAlchemy
│   ├── models/              # Modelos de base de datos
│   │   ├── user.py
│   │   ├── authority_profile.py
│   │   ├── instrument.py
│   │   ├── authority_instrument_assignment.py
│   │   └── document.py
│   ├── schemas/             # Schemas Pydantic
│   ├── services/            # Lógica de negocio
│   │   ├── auth_service.py
│   │   ├── authority_service.py
│   │   └── document_service.py
│   └── main.py              # Aplicación FastAPI
├── alembic/                 # Migraciones de base de datos
├── scripts/
│   └── seed.py              # Script de seed
├── tests/                   # Tests
├── uploads/                 # Archivos subidos
├── alembic.ini              # Configuración de Alembic
├── requirements.txt
└── .env.example

```

## 🔐 Endpoints principales

### Públicos (sin auth)
- `GET /public/` - Información general
- `GET /public/info` - Info de instrumentos y tipos de autoridad

### Autenticación
- `POST /auth/login` - Login (devuelve access + refresh token)
- `POST /auth/refresh` - Refrescar access token
- `GET /auth/me` - Info del usuario actual

### Admin (solo ADMIN)
- `POST /admin/authorities` - Crear autoridad turística
- `GET /admin/authorities` - Listar autoridades
- `GET /admin/authorities/{id}` - Detalle de autoridad
- `PATCH /admin/authorities/{id}` - Actualizar autoridad
- `GET /admin/documents` - Listar todos los documentos
- `DELETE /admin/documents/{id}` - Eliminar documento

### Autoridad (solo AUTHORITY)
- `GET /authority/documents?instrument=RURAL` - Listar documentos de instrumento
- `POST /authority/documents` - Subir documento (solo líder)
- `PATCH /authority/documents/{id}` - Actualizar documento (solo líder)
- `DELETE /authority/documents/{id}` - Eliminar documento (solo líder)
- `GET /authority/documents/{id}/download` - Descargar documento

## 👥 Roles y permisos

### Usuario Público
- No requiere login
- Acceso solo a endpoints públicos

### Autoridad Turística
- Requiere login
- Tipos: MUNICIPIO, DEPARTAMENTO, REGION, INDEPENDIENTE
- Debe tener exactamente 3 instrumentos asignados
- Por cada instrumento puede ser:
  - **Líder de Planificación**: Puede crear/editar/eliminar documentos
  - **Aliado Estratégico**: Solo puede ver documentos

### Administrador
- Requiere login
- Puede crear y gestionar autoridades
- Puede ver y gestionar todos los documentos
- Acceso total al sistema

## 🔒 Reglas de negocio

1. **Instrumentos por autoridad**: Cada autoridad debe tener exactamente 3 instrumentos asignados
2. **Líder único**: Solo puede haber 1 líder por instrumento en toda la plataforma
3. **Máximo aliados**: Máximo 8 aliados estratégicos por instrumento
4. **Permisos de documentos**:
   - Solo el líder puede crear/editar/eliminar documentos de su instrumento
   - Aliados solo pueden ver documentos
   - Admin puede ver/editar/eliminar todos los documentos

## 🛠️ Tecnologías

- **FastAPI** - Framework web moderno y rápido
- **SQLAlchemy 2.0** - ORM para Python
- **Alembic** - Migraciones de base de datos
- **PostgreSQL** - Base de datos relacional
- **Pydantic** - Validación de datos
- **JWT** - Autenticación con tokens
- **Passlib + Bcrypt** - Hashing de passwords
- **Pytest** - Framework de testing

## 📝 Notas importantes

1. **Cambiar SECRET_KEY en producción**: El SECRET_KEY del `.env.example` es solo para desarrollo
2. **Cambiar contraseña de admin**: Después del primer seed, cambia la contraseña del administrador
3. **Archivos subidos**: Los archivos se guardan en `uploads/` - configura un volumen persistente en producción
4. **CORS**: Ajusta `BACKEND_CORS_ORIGINS` en `.env` según tus necesidades

## 🐛 Troubleshooting

### Error de conexión a PostgreSQL
```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql

# Verificar credenciales en .env
```

### Error en migraciones
```bash
# Reiniciar migraciones
alembic downgrade base
alembic upgrade head
```

### Problemas con dependencias
```bash
# Reinstalar dependencias
pip install --upgrade -r requirements.txt
```
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
