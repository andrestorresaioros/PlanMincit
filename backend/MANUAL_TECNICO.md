# 📘 Manual Técnico - PlanMinCIT Backend

## Sistema de Planificación Turística del Ministerio de Comercio, Industria y Turismo

**Versión:** 1.0.0  
**Última actualización:** 21 de enero de 2026  
**Framework:** FastAPI  
**Base de datos:** PostgreSQL 14+  
**Python:** 3.10+

---

## 📑 Tabla de Contenidos

1. [Descripción General](#1-descripción-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Requisitos del Sistema](#3-requisitos-del-sistema)
4. [Instalación y Configuración](#4-instalación-y-configuración)
5. [Estructura del Proyecto](#5-estructura-del-proyecto)
6. [Modelos de Datos](#6-modelos-de-datos)
7. [API Endpoints](#7-api-endpoints)
8. [Servicios de Negocio](#8-servicios-de-negocio)
9. [Sistema de Autenticación](#9-sistema-de-autenticación)
10. [Sistema OAuth 2.0 / SSO](#10-sistema-oauth-20--sso)
11. [Gestión de Documentos](#11-gestión-de-documentos)
12. [Validaciones y Reglas de Negocio](#12-validaciones-y-reglas-de-negocio)
13. [Migraciones de Base de Datos](#13-migraciones-de-base-de-datos)
14. [Testing](#14-testing)
15. [Despliegue](#15-despliegue)
16. [Troubleshooting](#16-troubleshooting)
17. [Glosario](#17-glosario)

---

## 1. Descripción General

### 1.1 Propósito

PlanMinCIT Backend es una API REST desarrollada con **FastAPI** para la gestión integral de planificación turística territorial del Ministerio de Comercio, Industria y Turismo (MinCIT) de Colombia.

### 1.2 Características Principales

| Característica | Descripción |
|----------------|-------------|
| **Autenticación JWT** | Tokens de acceso (15 min) y refresco (7 días) |
| **OAuth 2.0 / SSO** | Flujo Authorization Code para portales externos |
| **RBAC** | Control de acceso basado en roles (Admin, Authority) |
| **Instrumentos de Planificación** | RURAL, URBANO, REGION |
| **Gestión de Autoridades** | Municipio, Departamento, Región, Independiente |
| **Gestión de Documentos** | Upload, download, metadatos con control de acceso |
| **Integración NDTT** | Conexión con API externa del NDTT |

### 1.3 Roles del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         ROLES DEL SISTEMA                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔐 ADMIN                                                       │
│  ├── Crear/Gestionar autoridades turísticas                    │
│  ├── Ver/Editar/Eliminar todos los documentos                  │
│  ├── Gestionar clientes OAuth                                  │
│  └── Acceso completo al sistema                                │
│                                                                 │
│  👤 AUTHORITY (Autoridad Turística)                             │
│  ├── Tipos: MUNICIPIO, DEPARTAMENTO, REGION, INDEPENDIENTE     │
│  ├── Roles por instrumento:                                    │
│  │   ├── LEADER_PLANNING: Crear/Editar/Eliminar documentos     │
│  │   └── STRATEGIC_ALLY: Solo lectura de documentos            │
│  └── Máximo 3 instrumentos asignados                           │
│                                                                 │
│  🌐 PÚBLICO                                                     │
│  └── Acceso a endpoints públicos (sin autenticación)           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTE (Frontend)                             │
│                          (React / Next.js - Puerto 3000)                    │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ HTTP/HTTPS
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI APPLICATION                             │
│                                 (Puerto 8000)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Routers   │    │ Middlewares │    │Dependencies │    │  Services   │  │
│  │  (API)      │    │ (CORS/Auth) │    │ (Auth/DB)   │    │  (Business) │  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
│         │                  │                  │                  │          │
│         └──────────────────┴──────────────────┴──────────────────┘          │
│                                     │                                        │
│                              ┌──────┴──────┐                                │
│                              │   Models    │                                │
│                              │ (SQLAlchemy)│                                │
│                              └──────┬──────┘                                │
│                                     │                                        │
└─────────────────────────────────────┼────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              POSTGRESQL DATABASE                             │
│                                 (Puerto 5432/5433)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────────┐  ┌───────────────────────────┐   │
│  │   users     │  │ authority_profiles  │  │ authority_instrument_     │   │
│  │             │  │                     │  │ assignments               │   │
│  └─────────────┘  └─────────────────────┘  └───────────────────────────┘   │
│  ┌─────────────┐  ┌─────────────────────┐  ┌───────────────────────────┐   │
│  │ instruments │  │     documents       │  │    oauth_* tables         │   │
│  └─────────────┘  └─────────────────────┘  └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Capas de la Aplicación

```
┌──────────────────────────────────────────────────────────────┐
│                      CAPAS DE LA APLICACIÓN                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📡 CAPA DE PRESENTACIÓN (API Layer)                         │
│  └── app/api/routers/                                        │
│      ├── public.py      → Endpoints públicos                 │
│      ├── auth.py        → Autenticación JWT                  │
│      ├── admin.py       → Gestión administrativa             │
│      ├── authority.py   → Operaciones de autoridades         │
│      └── oauth.py       → Flujo OAuth 2.0                    │
│                                                              │
│  🔒 CAPA DE SEGURIDAD (Security Layer)                       │
│  └── app/api/dependencies/                                   │
│      └── auth.py        → Dependencias de autenticación      │
│  └── app/core/                                               │
│      ├── security.py    → JWT y hashing                      │
│      └── oauth_security.py → Tokens OAuth                    │
│                                                              │
│  ⚙️ CAPA DE NEGOCIO (Business Layer)                         │
│  └── app/services/                                           │
│      ├── auth_service.py      → Lógica de autenticación      │
│      ├── authority_service.py → Gestión de autoridades       │
│      ├── document_service.py  → Gestión de documentos        │
│      ├── oauth_service.py     → Lógica OAuth                 │
│      ├── oauth_client_service.py → Gestión clientes OAuth    │
│      └── ndtt_service.py      → Integración NDTT externa     │
│                                                              │
│  💾 CAPA DE DATOS (Data Layer)                               │
│  └── app/models/                                             │
│      ├── user.py                                             │
│      ├── authority_profile.py                                │
│      ├── instrument.py                                       │
│      ├── authority_instrument_assignment.py                  │
│      ├── document.py                                         │
│      └── oauth_*.py (client, auth_code, access_token, etc.)  │
│                                                              │
│  📋 CAPA DE VALIDACIÓN (Validation Layer)                    │
│  └── app/schemas/                                            │
│      ├── auth.py, authority.py, document.py                  │
│      ├── instrument.py, user.py                              │
│      └── oauth.py, oauth_client.py, ndtt.py                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Requisitos del Sistema

### 3.1 Requisitos de Software

| Componente | Versión Mínima | Recomendada |
|------------|----------------|-------------|
| Python | 3.10+ | 3.11 |
| PostgreSQL | 14+ | 15 |
| pip | 21+ | Última |

### 3.2 Dependencias Principales

```txt
# Framework y servidor
fastapi==0.115.5          # Framework web asíncrono
uvicorn[standard]==0.32.1 # Servidor ASGI

# Validación y configuración
pydantic==2.10.3          # Validación de datos
pydantic-settings==2.6.1  # Gestión de configuración
python-dotenv==1.0.1      # Variables de entorno
email-validator==2.1.0    # Validación de emails

# Base de datos
sqlalchemy==2.0.36        # ORM
alembic==1.14.0           # Migraciones
psycopg2-binary==2.9.10   # Driver PostgreSQL

# Autenticación y seguridad
python-jose[cryptography]==3.3.0  # JWT
passlib[bcrypt]==1.7.4            # Hashing de contraseñas
python-multipart==0.0.18          # Uploads de archivos

# Templates y sesiones
jinja2==3.1.3             # Templates HTML (OAuth login)
itsdangerous==2.1.2       # Sesiones seguras

# Testing
pytest==8.3.4             # Framework de testing
httpx==0.27.2             # Cliente HTTP async
pytest-asyncio==0.23.5    # Soporte async para pytest

# Utilidades
requests==2.32.5          # Cliente HTTP (integraciones)
tqdm==4.67.1              # Barras de progreso
```

---

## 4. Instalación y Configuración

### 4.1 Instalación Local

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd backend

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con configuraciones apropiadas
```

### 4.2 Variables de Entorno

```env
# === Base de Datos ===
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/planmincit

# === Seguridad ===
SECRET_KEY=tu-secret-key-de-32-caracteres-minimo  # Generar con: openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# === Usuario Administrador Inicial ===
ADMIN_EMAIL=admin@planmincit.gov.co
ADMIN_PASSWORD=CambiaEstaContraseña123!

# === Archivos ===
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE=10485760  # 10MB en bytes

# === CORS ===
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# === NDTT (Integración externa) ===
NDTT_EMAIL=turismo40@gmail.com
NDTT_PASSWORD=Abcd$1234
```

### 4.3 Configuración de Base de Datos

```bash
# Conectar a PostgreSQL
psql -U postgres

# Crear base de datos
CREATE DATABASE planmincit;
\q

# Ejecutar migraciones
alembic upgrade head

# Ejecutar seed inicial
python scripts/seed.py
```

### 4.4 Ejecución

```bash
# Desarrollo (con hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 5. Estructura del Proyecto

```
backend/
├── 📁 alembic/                    # Migraciones de BD
│   ├── env.py                     # Configuración de Alembic
│   ├── script.py.mako             # Template de migraciones
│   └── 📁 versions/               # Archivos de migración
│       ├── 5a11329f4204_initial_migration.py
│       ├── fd565194c4f7_add_phase_and_component_to_documents.py
│       ├── ea6f6e1b0f65_add_territory_name_to_assignments.py
│       ├── 26e9227ca00f_add_territorial_codes_to_authority_.py
│       └── 52051817e8c1_add_territory_name_to_documents.py
│
├── 📁 app/                        # Aplicación principal
│   ├── __init__.py
│   ├── main.py                    # Punto de entrada FastAPI
│   │
│   ├── 📁 api/                    # Capa de API
│   │   ├── __init__.py
│   │   ├── 📁 dependencies/       # Dependencias de inyección
│   │   │   ├── __init__.py
│   │   │   └── auth.py            # Autenticación y autorización
│   │   └── 📁 routers/            # Endpoints
│   │       ├── __init__.py
│   │       ├── admin.py           # Endpoints administrativos
│   │       ├── auth.py            # Autenticación JWT
│   │       ├── authority.py       # Operaciones de autoridades
│   │       ├── oauth.py           # OAuth 2.0 / SSO
│   │       └── public.py          # Endpoints públicos
│   │
│   ├── 📁 core/                   # Configuración central
│   │   ├── __init__.py
│   │   ├── config.py              # Settings con Pydantic
│   │   ├── security.py            # JWT y password hashing
│   │   └── oauth_security.py      # Tokens OAuth
│   │
│   ├── 📁 data_sources/           # Fuentes de datos estáticas
│   │   ├── __init__.py
│   │   └── diccionario_municipios.py  # Códigos DANE
│   │
│   ├── 📁 db/                     # Base de datos
│   │   ├── __init__.py
│   │   └── session.py             # Configuración SQLAlchemy
│   │
│   ├── 📁 models/                 # Modelos ORM
│   │   ├── __init__.py
│   │   ├── user.py                # Usuario base
│   │   ├── authority_profile.py   # Perfil de autoridad
│   │   ├── instrument.py          # Instrumentos de planificación
│   │   ├── authority_instrument_assignment.py  # Asignaciones
│   │   ├── document.py            # Documentos
│   │   ├── oauth_client.py        # Clientes OAuth
│   │   ├── oauth_auth_code.py     # Códigos de autorización
│   │   ├── oauth_access_token.py  # Tokens de acceso
│   │   └── oauth_refresh_token.py # Tokens de refresco
│   │
│   ├── 📁 schemas/                # Schemas Pydantic
│   │   ├── __init__.py
│   │   ├── auth.py                # Login, Token, Me
│   │   ├── authority.py           # CRUD autoridades
│   │   ├── document.py            # CRUD documentos
│   │   ├── instrument.py          # Instrumentos
│   │   ├── ndtt.py                # Respuestas NDTT
│   │   ├── oauth.py               # Flujo OAuth
│   │   ├── oauth_client.py        # Clientes OAuth
│   │   └── user.py                # Usuario
│   │
│   ├── 📁 services/               # Lógica de negocio
│   │   ├── __init__.py
│   │   ├── auth_service.py        # Autenticación
│   │   ├── authority_service.py   # Gestión autoridades
│   │   ├── document_service.py    # Gestión documentos
│   │   ├── ndtt_service.py        # Integración NDTT
│   │   ├── oauth_service.py       # Flujo OAuth
│   │   └── oauth_client_service.py # Clientes OAuth
│   │
│   ├── 📁 templates/              # Templates HTML
│   │   └── oauth/
│   │       └── login.html         # Formulario login OAuth
│   │
│   └── 📁 utils/                  # Utilidades
│       ├── __init__.py
│       └── text_utils.py          # Normalización de texto
│
├── 📁 scripts/                    # Scripts de utilidad
│   ├── create_admin_user.py       # Crear usuario admin
│   ├── create_authority_user.py   # Crear autoridad de prueba
│   ├── create_oauth_clients.py    # Crear clientes OAuth
│   └── seed.py                    # Seed inicial
│
├── 📁 tests/                      # Tests
│   ├── __init__.py
│   └── test_api.py                # Tests de la API
│
├── 📁 uploads/                    # Archivos subidos
│   ├── rural/                     # Docs instrumento RURAL
│   └── urbano/                    # Docs instrumento URBANO
│
├── alembic.ini                    # Configuración Alembic
├── Dockerfile                     # Imagen Docker
├── pyproject.toml                 # Configuración pytest/coverage
├── requirements.txt               # Dependencias Python
├── README.md                      # Documentación básica
└── .env.example                   # Ejemplo de variables de entorno
```

---

## 6. Modelos de Datos

### 6.1 Diagrama Entidad-Relación

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DIAGRAMA ENTIDAD-RELACIÓN                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐         ┌─────────────────────────────┐
│       USERS         │         │    AUTHORITY_PROFILES       │
├─────────────────────┤         ├─────────────────────────────┤
│ id (PK)             │◄────────│ user_id (FK, UNIQUE)        │
│ email (UNIQUE)      │    1:1  │ id (PK)                     │
│ hashed_password     │         │ authority_type              │
│ is_active           │         │ display_name                │
│ role (ENUM)         │         │ additional_data             │
│ created_at          │         │ codigo_municipio            │
│ updated_at          │         │ codigo_departamento         │
└────────┬────────────┘         │ codigo_region               │
         │                      │ cedula                      │
         │                      └─────────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────────────────────────┐     ┌─────────────────────┐
│ AUTHORITY_INSTRUMENT_ASSIGNMENTS    │     │    INSTRUMENTS      │
├─────────────────────────────────────┤     ├─────────────────────┤
│ id (PK)                             │     │ id (PK)             │
│ authority_user_id (FK) ─────────────┼────►│ code (ENUM, UNIQUE) │
│ instrument_id (FK) ─────────────────┤     │ name                │
│ assignment_role (ENUM)              │     └────────┬────────────┘
│ territory_name                      │              │
│ created_at                          │              │
└─────────────────────────────────────┘              │
                                                     │ 1:N
         ┌───────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│           DOCUMENTS                 │
├─────────────────────────────────────┤
│ id (PK)                             │
│ instrument_id (FK)                  │
│ owner_authority_user_id (FK)        │
│ title                               │
│ description                         │
│ file_path                           │
│ original_filename                   │
│ content_type                        │
│ size_bytes                          │
│ phase                               │
│ component                           │
│ territory_name                      │
│ created_at                          │
│ updated_at                          │
└─────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                           TABLAS OAUTH 2.0                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐     ┌─────────────────────────┐
│   OAUTH_CLIENTS     │     │   OAUTH_AUTH_CODES      │
├─────────────────────┤     ├─────────────────────────┤
│ id (PK, UUID)       │◄────│ client_id (FK)          │
│ name                │     │ code (PK)               │
│ secret_hash         │     │ user_id (FK)            │
│ redirect_uri        │     │ redirect_uri            │
│ client_type         │     │ scopes (JSONB)          │
│ is_active           │     │ revoked                 │
│ created_at          │     │ expires_at              │
│ updated_at          │     └─────────────────────────┘
└─────────────────────┘
         │
         │
         ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│  OAUTH_ACCESS_TOKENS    │     │  OAUTH_REFRESH_TOKENS   │
├─────────────────────────┤     ├─────────────────────────┤
│ id (PK, UUID)           │◄────│ access_token_id (FK)    │
│ user_id (FK)            │     │ id (PK, UUID)           │
│ client_id (FK)          │     │ refresh_token_hash      │
│ access_token_hash       │     │ revoked                 │
│ refresh_token_hash      │     │ expires_at              │
│ scopes                  │     │ created_at              │
│ revoked                 │     └─────────────────────────┘
│ expires_at              │
│ created_at              │
└─────────────────────────┘
```

### 6.2 Modelo: User

```python
# app/models/user.py

class UserRole(str, enum.Enum):
    """Roles de usuario"""
    ADMIN = "ADMIN"           # Administrador del sistema
    AUTHORITY = "AUTHORITY"   # Autoridad turística

class User(Base):
    __tablename__ = "users"
    
    id: int                    # PK autoincremental
    email: str                 # Único, puede ser código DIVIPOLA
    hashed_password: str       # Hash bcrypt
    is_active: bool            # Estado de activación
    role: UserRole             # ADMIN o AUTHORITY
    created_at: datetime       # Fecha de creación
    updated_at: datetime       # Última modificación
    
    # Relaciones
    authority_profile          # 1:1 con AuthorityProfile
    instrument_assignments     # 1:N con AuthorityInstrumentAssignment
    documents                  # 1:N con Document
```

### 6.3 Modelo: AuthorityProfile

```python
# app/models/authority_profile.py

class AuthorityType(str, enum.Enum):
    """Tipos de autoridad turística"""
    MUNICIPIO = "MUNICIPIO"       # Autoridad municipal
    DEPARTAMENTO = "DEPARTAMENTO" # Autoridad departamental
    REGION = "REGION"             # Autoridad regional
    INDEPENDIENTE = "INDEPENDIENTE" # Autoridad independiente

class AuthorityProfile(Base):
    __tablename__ = "authority_profiles"
    
    id: int                    # PK
    user_id: int               # FK a users (UNIQUE)
    authority_type: AuthorityType
    display_name: str          # Nombre visible de la entidad
    additional_data: str       # JSON con datos adicionales
    codigo_municipio: str      # Código DANE municipio (5 dígitos)
    codigo_departamento: str   # Código DANE departamento (2 dígitos)
    codigo_region: str         # Código de región
    cedula: str                # Cédula (para INDEPENDIENTE)
```

### 6.4 Modelo: Instrument

```python
# app/models/instrument.py

class InstrumentCode(str, enum.Enum):
    """Códigos de instrumentos de planificación"""
    RURAL = "RURAL"    # Planificación Rural
    URBANO = "URBANO"  # Planificación Urbano
    REGION = "REGION"  # Planificación Regional

class Instrument(Base):
    __tablename__ = "instruments"
    
    id: int                    # PK
    code: InstrumentCode       # UNIQUE
    name: str                  # Nombre descriptivo
    
    # Relaciones
    assignments                # 1:N con asignaciones
    documents                  # 1:N con documentos
```

### 6.5 Modelo: AuthorityInstrumentAssignment

```python
# app/models/authority_instrument_assignment.py

class AssignmentRole(str, enum.Enum):
    """Roles de asignación a instrumentos"""
    LEADER_PLANNING = "LEADER_PLANNING"  # Líder de planificación
    STRATEGIC_ALLY = "STRATEGIC_ALLY"    # Aliado estratégico

class AuthorityInstrumentAssignment(Base):
    __tablename__ = "authority_instrument_assignments"
    
    id: int                    # PK
    authority_user_id: int     # FK a users
    instrument_id: int         # FK a instruments
    assignment_role: AssignmentRole
    territory_name: str        # Territorio asignado
    created_at: datetime
    
    # Constraints
    # UNIQUE(authority_user_id, instrument_id) - Un usuario solo 1 rol por instrumento
```

### 6.6 Modelo: Document

```python
# app/models/document.py

class Document(Base):
    __tablename__ = "documents"
    
    id: int                          # PK
    instrument_id: int               # FK a instruments
    owner_authority_user_id: int     # FK a users (propietario)
    title: str                       # Título del documento
    description: str                 # Descripción opcional
    file_path: str                   # Ruta física del archivo
    original_filename: str           # Nombre original
    content_type: str                # MIME type
    size_bytes: int                  # Tamaño en bytes
    phase: str                       # Fase (Alistamiento, Diagnóstico, etc.)
    component: str                   # Componente del plan
    territory_name: str              # Territorio asociado
    created_at: datetime
    updated_at: datetime
```

---

## 7. API Endpoints

### 7.1 Resumen de Endpoints

| Grupo | Prefijo | Auth | Descripción |
|-------|---------|------|-------------|
| Public | `/public` | ❌ | Información pública |
| Auth | `/auth` | ⚠️ | Autenticación JWT |
| Admin | `/admin` | ✅ ADMIN | Gestión administrativa |
| Authority | `/authority` | ✅ AUTHORITY | Operaciones de autoridades |
| OAuth | `/oauth` | ⚠️ | Flujo OAuth 2.0 / SSO |

### 7.2 Endpoints Públicos

```
GET  /                    → Root endpoint (info API)
GET  /health              → Health check
GET  /public/             → Página de bienvenida
GET  /public/home         → Alias de /public/
GET  /public/info         → Información de instrumentos y tipos
```

**Ejemplo de respuesta `/public/info`:**
```json
{
  "platform": "PlanMinCIT",
  "ministry": "Ministerio de Comercio, Industria y Turismo",
  "instruments": [
    {"code": "RURAL", "name": "Instrumento de Planificación Rural"},
    {"code": "URBANO", "name": "Instrumento de Planificación Urbano"},
    {"code": "REGION", "name": "Instrumento de Planificación Regional"}
  ],
  "authority_types": ["MUNICIPIO", "DEPARTAMENTO", "REGION", "INDEPENDIENTE"]
}
```

### 7.3 Endpoints de Autenticación

```
POST /auth/login          → Iniciar sesión (devuelve JWT)
POST /auth/refresh        → Refrescar access token
GET  /auth/me             → Información del usuario actual
```

**Request `/auth/login`:**
```json
{
  "email": "admin@planmincit.gov.co",
  "password": "Admin123!"
}
```

**Response `/auth/login`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Response `/auth/me` (Authority):**
```json
{
  "id": 5,
  "email": "17013",
  "role": "AUTHORITY",
  "is_active": true,
  "authority_type": "MUNICIPIO",
  "display_name": "Municipio de Aguadas",
  "instrument_assignments": [
    {
      "instrument_code": "RURAL",
      "instrument_name": "Instrumento de Planificación Rural",
      "role": "LEADER_PLANNING",
      "role_display": "lider de planificacion",
      "territory_name": "Aguadas"
    }
  ]
}
```

### 7.4 Endpoints de Administración

```
# === Autoridades ===
POST   /admin/authorities              → Crear autoridad
GET    /admin/authorities              → Listar autoridades
GET    /admin/authorities/{id}         → Detalle de autoridad
PATCH  /admin/authorities/{id}         → Actualizar autoridad
DELETE /admin/authorities/{id}         → Eliminar autoridad

# === Documentos ===
GET    /admin/documents                → Listar todos los documentos
PATCH  /admin/documents/{id}           → Actualizar documento
DELETE /admin/documents/{id}           → Eliminar documento
DELETE /admin/authorities/{id}/instruments/{code}/documents → Eliminar docs por instrumento

# === OAuth Clients ===
POST   /admin/oauth/clients            → Crear cliente OAuth
GET    /admin/oauth/clients            → Listar clientes OAuth
POST   /admin/oauth/clients/{id}/revoke → Revocar cliente OAuth

# === Territorios ===
GET    /admin/territorios              → Listar municipios y departamentos DIVIPOLA
```

**Request `POST /admin/authorities`:**
```json
{
  "email": "contacto@aguadas.gov.co",
  "password": "Password123!",
  "authority_type": "MUNICIPIO",
  "display_name": "Municipio de Aguadas",
  "main_territory": "Aguadas",
  "instrument_assignments": [
    {
      "instrument_code": "RURAL",
      "role": "LEADER_PLANNING",
      "territory_name": "Aguadas"
    }
  ]
}
```

### 7.5 Endpoints de Autoridad

```
# === Documentos ===
GET    /authority/documents                    → Listar documentos (por instrumento)
POST   /authority/documents                    → Subir documento (solo líder)
PATCH  /authority/documents/{id}               → Actualizar documento
DELETE /authority/documents/{id}               → Eliminar documento
GET    /authority/documents/{id}/download      → Descargar documento

# === Por fase/componente ===
GET    /authority/{instrument}/{phase}/{component}/documents

# === NDTT Report ===
GET    /authority/ndtt-report                  → Obtener reporte NDTT

# === Público con código ===
GET    /{codigo}/{instrument}/{phase}/{component}/documents
GET    /documents-by-authority                 → Documentos jerárquicos
```

**Request `POST /authority/documents` (multipart/form-data):**
```
instrument_code: RURAL
title: Plan de Desarrollo 2026
description: Documento de planificación
phase: Alistamiento
component: participacion-social
file: [archivo.pdf]
```

### 7.6 Endpoints OAuth 2.0

```
GET  /oauth/login          → Formulario de login HTML
POST /oauth/login          → Submit de login
POST /oauth/session        → Crear sesión SSO desde JWT
POST /oauth/logout         → Cerrar sesión SSO
GET  /oauth/authorize      → Endpoint de autorización (Authorization Code)
POST /oauth/token          → Intercambiar code por tokens
GET  /oauth/userinfo       → Información del usuario autenticado
```

---

## 8. Servicios de Negocio

### 8.1 AuthService

Ubicación: `app/services/auth_service.py`

```python
class AuthService:
    @staticmethod
    def authenticate_user(db, email, password) -> Optional[User]:
        """Autenticar usuario por email y contraseña"""
    
    @staticmethod
    def create_tokens(user) -> dict:
        """Crear tokens de acceso y refresco"""
        # Retorna: {access_token, refresh_token, token_type}
    
    @staticmethod
    def refresh_access_token(refresh_token, db) -> dict:
        """Renovar access token usando refresh token"""
    
    @staticmethod
    def get_user_by_id(db, user_id) -> Optional[User]:
        """Obtener usuario por ID"""
```

### 8.2 AuthorityService

Ubicación: `app/services/authority_service.py`

```python
class AuthorityService:
    @staticmethod
    def validate_instrument_assignments(db, assignments, exclude_user_id=None):
        """
        Validar asignaciones de instrumentos:
        - Mínimo 1 instrumento
        - 1 líder máximo por instrumento+territorio
        - 10 aliados máximo por instrumento+territorio
        - Aliado solo si existe líder en ese territorio
        """
    
    @staticmethod
    def create_authority_user(db, data: AuthorityCreateRequest) -> User:
        """
        Crear usuario autoridad con:
        - Usuario (email o código DIVIPOLA)
        - Perfil de autoridad
        - Asignaciones de instrumentos
        """
    
    @staticmethod
    def get_authority_users(db) -> List[User]:
        """Listar todas las autoridades"""
    
    @staticmethod
    def get_authority_by_id(db, user_id) -> Optional[User]:
        """Obtener autoridad por ID"""
    
    @staticmethod
    def update_authority(db, user_id, update_data) -> User:
        """Actualizar datos de autoridad"""
    
    @staticmethod
    def delete_authority(db, user_id) -> dict:
        """Eliminar autoridad y sus documentos"""
```

### 8.3 DocumentService

Ubicación: `app/services/document_service.py`

```python
class DocumentService:
    @staticmethod
    def check_user_has_instrument_access(db, user_id, instrument_code):
        """Verificar si usuario tiene acceso al instrumento"""
    
    @staticmethod
    def check_user_is_instrument_leader(db, user_id, instrument_code) -> bool:
        """Verificar si usuario es líder del instrumento"""
    
    @staticmethod
    async def save_uploaded_file(file, instrument_code) -> tuple[str, int]:
        """
        Guardar archivo en disco:
        - Crear directorio si no existe
        - Validar extensión permitida
        - Validar tamaño máximo (10MB)
        - Retorna: (file_path, size_bytes)
        """
    
    @staticmethod
    async def create_document(db, user, instrument_code, title, description, file, ...):
        """Crear documento (solo líderes)"""
    
    @staticmethod
    def get_documents_by_instrument(db, user, instrument_code, territory_name=None):
        """Obtener documentos por instrumento con permisos"""
    
    @staticmethod
    def update_document(db, user, document_id, update_data):
        """Actualizar metadatos de documento"""
    
    @staticmethod
    def delete_document(db, user, document_id):
        """Eliminar documento (archivo + registro)"""
    
    @staticmethod
    def get_documents_by_authority_hierarchical(db, ...):
        """Obtener documentos en estructura jerárquica"""
```

### 8.4 OAuthService

Ubicación: `app/services/oauth_service.py`

```python
class OAuthService:
    @staticmethod
    def get_client(db, client_id) -> OAuthClient:
        """Obtener cliente OAuth validando que esté activo"""
    
    @staticmethod
    def validate_client_secret(client, client_secret):
        """Validar secreto del cliente"""
    
    @staticmethod
    def create_auth_code(db, user_id, client, redirect_uri, scopes) -> str:
        """
        Crear código de autorización:
        - Validar redirect_uri
        - Generar código único
        - Expiración: 10 minutos
        """
    
    @staticmethod
    def exchange_code_for_tokens(db, client, code, redirect_uri):
        """
        Intercambiar code por tokens:
        - Validar code no expirado ni revocado
        - Consumir code (marcar como revocado)
        - Generar access_token y refresh_token
        - Retorna: (access_token, refresh_token, ttl)
        """
    
    @staticmethod
    def get_user_from_access_token(db, access_token):
        """Obtener usuario desde access token OAuth"""
```

### 8.5 NDTTService

Ubicación: `app/services/ndtt_service.py`

```python
class NDTTService:
    @staticmethod
    def _get_auth_token() -> Optional[str]:
        """Obtener token de autenticación del API NDTT"""
    
    @staticmethod
    def get_municipio_info(nombre_municipio) -> Optional[Dict]:
        """
        Obtener información del municipio:
        - Buscar código DANE en diccionario
        - Autenticarse con API NDTT
        - Consultar información del municipio
        """
    
    @staticmethod
    def get_codigo_municipio(nombre_municipio) -> str:
        """Obtener código DANE de municipio por nombre"""
    
    @staticmethod
    def get_codigo_departamento(nombre_departamento) -> str:
        """Obtener código DANE de departamento por nombre"""
```

---

## 9. Sistema de Autenticación

### 9.1 Flujo de Autenticación JWT

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FLUJO DE AUTENTICACIÓN JWT                            │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌─────────┐                              ┌─────────────┐
     │ Cliente │                              │   Backend   │
     └────┬────┘                              └──────┬──────┘
          │                                          │
          │  1. POST /auth/login                     │
          │  {email, password}                       │
          │ ────────────────────────────────────────►│
          │                                          │
          │                          2. Verificar    │
          │                             credenciales │
          │                                          │
          │  3. {access_token, refresh_token}        │
          │ ◄────────────────────────────────────────│
          │                                          │
          │  4. GET /auth/me                         │
          │  Authorization: Bearer <access_token>    │
          │ ────────────────────────────────────────►│
          │                                          │
          │                          5. Decodificar  │
          │                             y validar    │
          │                             token        │
          │                                          │
          │  6. {user_info}                          │
          │ ◄────────────────────────────────────────│
          │                                          │
          │        ... Access Token Expira ...       │
          │                                          │
          │  7. POST /auth/refresh                   │
          │  {refresh_token}                         │
          │ ────────────────────────────────────────►│
          │                                          │
          │  8. {access_token (nuevo)}               │
          │ ◄────────────────────────────────────────│
          │                                          │
```

### 9.2 Estructura de Tokens JWT

**Access Token (15 minutos):**
```json
{
  "sub": "5",           // User ID
  "email": "17013",     // Email o código DIVIPOLA
  "role": "AUTHORITY",  // Rol del usuario
  "exp": 1737475200,    // Expiración (Unix timestamp)
  "type": "access"      // Tipo de token
}
```

**Refresh Token (7 días):**
```json
{
  "sub": "5",
  "email": "17013",
  "role": "AUTHORITY",
  "exp": 1738080000,
  "type": "refresh"
}
```

### 9.3 Dependencias de Seguridad

```python
# app/api/dependencies/auth.py

# Obtener usuario actual (requiere token válido)
async def get_current_user(credentials, db) -> User:
    """
    - Decodificar JWT
    - Validar que sea access token
    - Verificar usuario activo
    """

# Requerir rol de administrador
async def require_admin(current_user) -> User:
    """Lanza 403 si no es ADMIN"""

# Requerir rol de autoridad
async def require_authority(current_user) -> User:
    """Lanza 403 si no es AUTHORITY"""

# Requerir acceso a instrumento específico
def require_instrument_access(instrument_code):
    """Factory que retorna dependencia para validar acceso"""

# Requerir ser líder de instrumento
def require_instrument_leader(instrument_code):
    """Factory que retorna dependencia para validar rol de líder"""
```

### 9.4 Configuración de Seguridad

```python
# app/core/security.py

# Algoritmo: HS256
# Context: bcrypt

def verify_password(plain, hashed) -> bool
def get_password_hash(password) -> str
def create_access_token(data, expires_delta=None) -> str
def create_refresh_token(data) -> str
def decode_token(token) -> Optional[dict]
```

---

## 10. Sistema OAuth 2.0 / SSO

### 10.1 Flujo Authorization Code

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FLUJO OAUTH 2.0 AUTHORIZATION CODE                       │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐        ┌──────────────┐        ┌─────────────┐
  │  Usuario │        │ Portal (RP)  │        │ PlanMinCIT  │
  │          │        │              │        │ (IdP/OAuth) │
  └────┬─────┘        └──────┬───────┘        └──────┬──────┘
       │                     │                       │
       │  1. Click "Login    │                       │
       │     con MinCIT"     │                       │
       │ ───────────────────►│                       │
       │                     │                       │
       │                     │  2. Redirect a:       │
       │                     │  /oauth/authorize     │
       │ ◄───────────────────│  ?client_id=...      │
       │                     │  &redirect_uri=...   │
       │                     │  &response_type=code │
       │                     │  &state=xyz          │
       │ ──────────────────────────────────────────►│
       │                     │                       │
       │                     │     3. ¿Hay sesión?   │
       │                     │        Si no: Login   │
       │  4. Form login      │                       │
       │ ◄──────────────────────────────────────────│
       │                     │                       │
       │  5. email+password  │                       │
       │ ──────────────────────────────────────────►│
       │                     │                       │
       │                     │     6. Crear auth_code│
       │                     │        (válido 10min) │
       │                     │                       │
       │  7. Redirect a:     │                       │
       │  redirect_uri       │                       │
       │  ?code=abc&state=xyz│                       │
       │ ◄──────────────────────────────────────────│
       │ ───────────────────►│                       │
       │                     │                       │
       │                     │  8. POST /oauth/token │
       │                     │  {client_id,          │
       │                     │   client_secret,      │
       │                     │   code, redirect_uri} │
       │                     │ ─────────────────────►│
       │                     │                       │
       │                     │  9. {access_token,    │
       │                     │      refresh_token}   │
       │                     │ ◄─────────────────────│
       │                     │                       │
       │                     │  10. GET /oauth/userinfo
       │                     │  Authorization: Bearer │
       │                     │ ─────────────────────►│
       │                     │                       │
       │                     │  11. {id, email,      │
       │                     │       role, ...}      │
       │                     │ ◄─────────────────────│
       │                     │                       │
       │  12. Sesión local   │                       │
       │      creada         │                       │
       │ ◄───────────────────│                       │
       │                     │                       │
```

### 10.2 Crear Cliente OAuth

```bash
# Como admin, crear cliente OAuth
POST /admin/oauth/clients
{
  "name": "Portal Turismo",
  "client_type": "municipio",
  "redirect_uri": "https://portal-turismo.gov.co/callback"
}

# Respuesta (GUARDAR - el secret solo se muestra una vez):
{
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_secret": "XxYyZz123...abc",
  "name": "Portal Turismo",
  "client_type": "municipio",
  "redirect_uri": "https://portal-turismo.gov.co/callback"
}
```

### 10.3 Puente JWT → Sesión SSO

Para usuarios que ya tienen JWT (login normal), pueden crear sesión SSO:

```python
POST /oauth/session
Authorization: Bearer <jwt_access_token>

# Crea cookie de sesión SSO para el flujo OAuth
```

---

## 11. Gestión de Documentos

### 11.1 Flujo de Upload

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUJO DE UPLOAD DE DOCUMENTO                         │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌───────────┐                              ┌─────────────┐
    │  Cliente  │                              │   Backend   │
    └─────┬─────┘                              └──────┬──────┘
          │                                           │
          │  POST /authority/documents                │
          │  Content-Type: multipart/form-data        │
          │  Authorization: Bearer <token>            │
          │  ─────────────────────────────────────────►
          │                                           │
          │                           ┌───────────────┴───────────────┐
          │                           │ 1. Validar token (require_authority)
          │                           │ 2. Verificar rol LEADER_PLANNING
          │                           │ 3. Validar extensión archivo
          │                           │    (.pdf, .doc, .docx, .xls, .xlsx, .zip)
          │                           │ 4. Validar tamaño < 10MB
          │                           │ 5. Guardar archivo en:
          │                           │    uploads/{instrument_code}/{timestamp}_{filename}
          │                           │ 6. Crear registro en DB
          │                           └───────────────┬───────────────┘
          │                                           │
          │  201 Created                              │
          │  {id, title, download_url, ...}           │
          │  ◄─────────────────────────────────────────
          │                                           │
```

### 11.2 Estructura de Almacenamiento

```
uploads/
├── rural/
│   ├── 1737475200_documento_plan.pdf
│   ├── 1737475300_anexo_participacion.docx
│   └── ...
├── urbano/
│   ├── 1737476000_plan_urbano.pdf
│   └── ...
└── region/
    └── ...
```

### 11.3 Extensiones Permitidas

| Extensión | Tipo |
|-----------|------|
| `.pdf` | Documento PDF |
| `.doc` | Word 97-2003 |
| `.docx` | Word moderno |
| `.xls` | Excel 97-2003 |
| `.xlsx` | Excel moderno |
| `.zip` | Archivo comprimido |

### 11.4 Permisos por Rol

| Acción | ADMIN | LEADER | ALLY |
|--------|-------|--------|------|
| Ver documentos propios | ✅ | ✅ | ✅ |
| Ver docs del territorio | ✅ | ✅ | ✅ |
| Ver todos los documentos | ✅ | ❌ | ❌ |
| Crear documentos | ✅ | ✅ | ❌ |
| Editar documentos propios | ✅ | ✅ | ❌ |
| Editar cualquier documento | ✅ | ❌ | ❌ |
| Eliminar documentos propios | ✅ | ✅ | ❌ |
| Eliminar cualquier documento | ✅ | ❌ | ❌ |

---

## 12. Validaciones y Reglas de Negocio

### 12.1 Reglas de Asignación de Instrumentos

```python
# Regla 1: Mínimo 1 instrumento por autoridad
if len(assignments) < 1:
    raise "Debe asignar al menos 1 instrumento"

# Regla 2: Sin duplicados de instrumento
if len(instrument_codes) != len(set(instrument_codes)):
    raise "No puede asignar el mismo instrumento más de una vez"

# Regla 3: Máximo 1 líder por instrumento + territorio
if assignment_role == LEADER_PLANNING:
    leaders_count = count(leaders_for_instrument_and_territory)
    if leaders_count >= 1:
        raise "Ya existe un líder para este instrumento y territorio"

# Regla 4: Máximo 10 aliados por instrumento + territorio
if assignment_role == STRATEGIC_ALLY:
    # Primero verificar que existe líder
    if not exists_leader_for_territory:
        raise "Debe haber un líder creado primero"
    
    allies_count = count(allies_for_instrument_and_territory)
    if allies_count >= 10:
        raise "Ya hay 10 aliados para este instrumento y territorio"
```

### 12.2 Reglas de Usuarios por Tipo

| Tipo | Email/Usuario | Identificador |
|------|---------------|---------------|
| MUNICIPIO | `{codigo_dane_5_digitos}` | Código DIVIPOLA municipio |
| DEPARTAMENTO | `{codigo_dane_2_digitos}` | Código DIVIPOLA departamento |
| REGION | `{email@domain.com}` | Email real |
| INDEPENDIENTE | `{cedula}` | Cédula de ciudadanía |

### 12.3 Validaciones de Documentos

```python
# Extensión permitida
if extension not in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip"}:
    raise "Tipo de archivo no permitido"

# Tamaño máximo
if size_bytes > 10 * 1024 * 1024:  # 10MB
    raise "Archivo demasiado grande"

# Solo líder puede crear
if not is_leader:
    raise "Solo el líder de planificación puede crear documentos"
```

---

## 13. Migraciones de Base de Datos

### 13.1 Comandos Alembic

```bash
# Ver estado actual
alembic current

# Crear nueva migración
alembic revision --autogenerate -m "descripcion_del_cambio"

# Aplicar migraciones pendientes
alembic upgrade head

# Revertir última migración
alembic downgrade -1

# Revertir todas las migraciones
alembic downgrade base

# Ver historial
alembic history
```

### 13.2 Migraciones Existentes

| Fecha | ID | Descripción |
|-------|-----|-------------|
| 2025-12-27 | `5a11329f4204` | Migración inicial (users, instruments, etc.) |
| 2026-01-05 | `fd565194c4f7` | Agregar phase y component a documents |
| 2026-01-05 | `ea6f6e1b0f65` | Agregar territory_name a assignments |
| 2026-01-10 | `26e9227ca00f` | Agregar códigos territoriales a authority_profile |
| 2026-01-13 | `52051817e8c1` | Agregar territory_name a documents |

### 13.3 Crear Nueva Migración

```bash
# 1. Modificar modelo en app/models/
# 2. Generar migración automática
alembic revision --autogenerate -m "add_new_field_to_table"

# 3. Revisar archivo generado en alembic/versions/
# 4. Aplicar
alembic upgrade head
```

---

## 14. Testing

### 14.1 Configuración de Tests

```python
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --strict-markers"

[tool.coverage.run]
source = ["app"]
omit = ["*/tests/*", "*/alembic/*"]
```

### 14.2 Ejecutar Tests

```bash
# Todos los tests
pytest tests/ -v

# Test específico
pytest tests/test_api.py::test_login_success -v

# Con cobertura
pytest tests/ -v --cov=app --cov-report=html

# Ver reporte HTML
open htmlcov/index.html
```

### 14.3 Estructura de Tests

```python
# tests/test_api.py

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Setup y teardown de BD para cada test"""
    Base.metadata.create_all(bind=engine)
    # Seed datos de prueba
    yield
    Base.metadata.drop_all(bind=engine)

def test_public_home():
    """Test endpoint público"""
    response = client.get("/public/")
    assert response.status_code == 200

def test_login_success():
    """Test login exitoso"""
    response = client.post("/auth/login", json={...})
    assert response.status_code == 200
    assert "access_token" in response.json()
```

---

## 15. Despliegue

### 15.1 Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 15.2 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/planmincit
    depends_on:
      - db
    volumes:
      - ./backend/uploads:/app/uploads

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=planmincit
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 15.3 Producción

```bash
# Ejecutar con múltiples workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Con gunicorn (recomendado)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 15.4 Checklist de Producción

- [ ] Cambiar `SECRET_KEY` por valor seguro
- [ ] Cambiar contraseña de admin
- [ ] Configurar HTTPS
- [ ] Configurar `BACKEND_CORS_ORIGINS` correctamente
- [ ] Volumen persistente para `uploads/`
- [ ] Backup de base de datos
- [ ] Configurar logging
- [ ] Monitoreo de salud (`/health`)

---

## 16. Troubleshooting

### 16.1 Errores Comunes

**Error de conexión a PostgreSQL:**
```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql

# Verificar credenciales
psql -U postgres -d planmincit

# Revisar DATABASE_URL en .env
```

**Error en migraciones:**
```bash
# Ver estado actual
alembic current

# Reiniciar migraciones
alembic downgrade base
alembic upgrade head
```

**Token inválido o expirado:**
```python
# Verificar configuración de tiempos
ACCESS_TOKEN_EXPIRE_MINUTES=15  # Muy corto para desarrollo
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Problemas CORS:**
```python
# Verificar orígenes permitidos
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

**Archivo no encontrado:**
```bash
# Verificar que existe el directorio uploads
ls -la uploads/

# Verificar permisos
chmod 755 uploads/
```

### 16.2 Logs de Debug

```python
# Habilitar en .env
DEBUG=True
DATABASE_ECHO=True  # Logs de SQL
```

---

## 17. Glosario

| Término | Definición |
|---------|------------|
| **Authority** | Usuario con rol de autoridad turística |
| **DIVIPOLA** | División Político-Administrativa de Colombia |
| **Instrument** | Instrumento de planificación (RURAL, URBANO, REGION) |
| **LEADER_PLANNING** | Rol de líder de planificación (puede CRUD documentos) |
| **STRATEGIC_ALLY** | Rol de aliado estratégico (solo lectura) |
| **NDTT** | Nodos de Desarrollo Turístico Territorial |
| **JWT** | JSON Web Token |
| **OAuth 2.0** | Protocolo de autorización |
| **SSO** | Single Sign-On |
| **RBAC** | Role-Based Access Control |
| **MinCIT** | Ministerio de Comercio, Industria y Turismo |

---

## 📞 Contacto y Soporte

Para soporte técnico o consultas sobre la API, contactar al equipo de desarrollo.

---

*Documento generado automáticamente. Última actualización: 21 de enero de 2026*
