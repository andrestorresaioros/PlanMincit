# 🧪 Ejemplos de uso de la API - PlanMinCIT

Ejemplos prácticos para probar todos los endpoints de la API.

## 📋 Requisitos previos

1. Tener el servidor corriendo: `uvicorn app.main:app --reload`
2. Tener la base de datos creada con seed ejecutado
3. Tener `curl` o usar Swagger UI en http://localhost:8000/docs

---

## 1️⃣ Autenticación

### Login como Administrador

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@planmincit.gov.co",
    "password": "Admin123!Change"
  }'
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

💡 Guarda el `access_token` para usarlo en las siguientes peticiones.

### Refrescar Token

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "TU_REFRESH_TOKEN_AQUI"
  }'
```

### Obtener información del usuario actual

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer TU_ACCESS_TOKEN"
```

---

## 2️⃣ Gestión de Autoridades (Admin)

### Crear Autoridad Turística como LÍDER de RURAL

```bash
curl -X POST http://localhost:8000/admin/authorities \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN" \
  -d '{
    "email": "lider.rural@cartagena.gov.co",
    "password": "SecurePass123!",
    "authority_type": "MUNICIPIO",
    "display_name": "Municipio de Cartagena",
    "metadata": "{\"region\": \"Caribe\", \"codigo_dane\": \"13001\"}",
    "instrument_assignments": [
      {
        "instrument_code": "RURAL",
        "role": "LEADER_PLANNING"
      },
      {
        "instrument_code": "URBANO",
        "role": "STRATEGIC_ALLY"
      },
      {
        "instrument_code": "REGION",
        "role": "STRATEGIC_ALLY"
      }
    ]
  }'
```

### Crear Autoridad como ALIADO de RURAL

```bash
curl -X POST http://localhost:8000/admin/authorities \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN" \
  -d '{
    "email": "aliado.rural@bolivar.gov.co",
    "password": "SecurePass123!",
    "authority_type": "DEPARTAMENTO",
    "display_name": "Departamento de Bolívar",
    "instrument_assignments": [
      {
        "instrument_code": "RURAL",
        "role": "STRATEGIC_ALLY"
      },
      {
        "instrument_code": "URBANO",
        "role": "LEADER_PLANNING"
      },
      {
        "instrument_code": "REGION",
        "role": "STRATEGIC_ALLY"
      }
    ]
  }'
```

### Listar todas las autoridades

```bash
curl -X GET http://localhost:8000/admin/authorities \
  -H "Authorization: Bearer TU_ACCESS_TOKEN"
```

### Obtener detalle de una autoridad

```bash
curl -X GET http://localhost:8000/admin/authorities/2 \
  -H "Authorization: Bearer TU_ACCESS_TOKEN"
```

### Actualizar autoridad

```bash
curl -X PATCH http://localhost:8000/admin/authorities/2 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN" \
  -d '{
    "display_name": "Municipio de Cartagena de Indias",
    "is_active": true
  }'
```

### Reasignar instrumentos de una autoridad

```bash
curl -X PATCH http://localhost:8000/admin/authorities/2 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN" \
  -d '{
    "instrument_assignments": [
      {
        "instrument_code": "RURAL",
        "role": "STRATEGIC_ALLY"
      },
      {
        "instrument_code": "URBANO",
        "role": "LEADER_PLANNING"
      },
      {
        "instrument_code": "REGION",
        "role": "STRATEGIC_ALLY"
      }
    ]
  }'
```

---

## 3️⃣ Gestión de Documentos (Autoridad)

### Login como Autoridad

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "lider.rural@cartagena.gov.co",
    "password": "SecurePass123!"
  }'
```

### Subir documento (solo LÍDER)

```bash
curl -X POST http://localhost:8000/authority/documents \
  -H "Authorization: Bearer TU_ACCESS_TOKEN_AUTORIDAD" \
  -F "instrument_code=RURAL" \
  -F "title=Plan de Desarrollo Turístico Rural 2024" \
  -F "description=Documento maestro con estrategias de turismo rural" \
  -F "file=@/ruta/a/tu/documento.pdf"
```

### Listar documentos de un instrumento

```bash
# Como líder o aliado del instrumento
curl -X GET "http://localhost:8000/authority/documents?instrument=RURAL" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN_AUTORIDAD"
```

### Actualizar documento (solo LÍDER)

```bash
curl -X PATCH http://localhost:8000/authority/documents/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN_AUTORIDAD" \
  -d '{
    "title": "Plan de Desarrollo Turístico Rural 2024 - Versión Final",
    "description": "Versión final aprobada por el consejo municipal"
  }'
```

### Descargar documento

```bash
# Como líder, aliado o admin
curl -X GET http://localhost:8000/authority/documents/1/download \
  -H "Authorization: Bearer TU_ACCESS_TOKEN_AUTORIDAD" \
  -O -J
```

### Eliminar documento (solo LÍDER)

```bash
curl -X DELETE http://localhost:8000/authority/documents/1 \
  -H "Authorization: Bearer TU_ACCESS_TOKEN_AUTORIDAD"
```

---

## 4️⃣ Gestión de Documentos (Admin)

### Listar todos los documentos

```bash
curl -X GET http://localhost:8000/admin/documents \
  -H "Authorization: Bearer TU_ACCESS_TOKEN_ADMIN"
```

### Editar cualquier documento

```bash
curl -X PATCH http://localhost:8000/admin/documents/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN_ADMIN" \
  -d '{
    "title": "Documento editado por admin",
    "description": "Correcciones administrativas"
  }'
```

### Eliminar cualquier documento

```bash
curl -X DELETE http://localhost:8000/admin/documents/1 \
  -H "Authorization: Bearer TU_ACCESS_TOKEN_ADMIN"
```

---

## 5️⃣ Endpoints Públicos (sin autenticación)

### Información general

```bash
curl -X GET http://localhost:8000/public/
```

### Información de instrumentos

```bash
curl -X GET http://localhost:8000/public/info
```

### Health check

```bash
curl -X GET http://localhost:8000/health
```

---

## 🚨 Casos de error comunes

### Intentar crear segundo líder (debe fallar)

```bash
# Este request debe retornar 400 Bad Request
curl -X POST http://localhost:8000/admin/authorities \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN" \
  -d '{
    "email": "otro.lider@test.com",
    "password": "Pass123!",
    "authority_type": "REGION",
    "display_name": "Otra Autoridad",
    "instrument_assignments": [
      {
        "instrument_code": "RURAL",
        "role": "LEADER_PLANNING"
      },
      {
        "instrument_code": "URBANO",
        "role": "STRATEGIC_ALLY"
      },
      {
        "instrument_code": "REGION",
        "role": "STRATEGIC_ALLY"
      }
    ]
  }'
```

**Error esperado:**
```json
{
  "detail": "Ya existe un líder para el instrumento RURAL"
}
```

### Intentar subir documento como aliado (debe fallar)

```bash
# Login como aliado primero
# Luego intentar subir documento - debe retornar 403 Forbidden
curl -X POST http://localhost:8000/authority/documents \
  -H "Authorization: Bearer ACCESS_TOKEN_ALIADO" \
  -F "instrument_code=RURAL" \
  -F "title=Test" \
  -F "file=@documento.pdf"
```

**Error esperado:**
```json
{
  "detail": "Solo el líder de planificación puede crear documentos para este instrumento"
}
```

### Acceder a instrumento sin asignación (debe fallar)

```bash
# Intentar ver documentos de instrumento al que no estás asignado
curl -X GET "http://localhost:8000/authority/documents?instrument=REGION" \
  -H "Authorization: Bearer TU_ACCESS_TOKEN"
```

**Error esperado:**
```json
{
  "detail": "No tiene acceso a este instrumento"
}
```

---

## 💡 Tips

1. **Guardar tokens**: Guarda el access_token en una variable de entorno:
   ```bash
   export TOKEN="tu_access_token_aqui"
   curl -H "Authorization: Bearer $TOKEN" ...
   ```

2. **Usar Swagger UI**: Más fácil para probar interactivamente: http://localhost:8000/docs

3. **Ver logs**: Ejecuta el servidor con `--log-level debug` para ver más información

4. **Testing completo**: Usa Postman o Insomnia e importa la colección desde Swagger

---

## 🎯 Flujo de trabajo típico

1. **Admin** crea autoridades con sus instrumentos asignados
2. **Líder** sube documentos de planificación
3. **Aliados** revisan y descargan los documentos
4. **Líder** actualiza documentos según feedback
5. **Admin** supervisa todo el proceso

---

## 📊 Estadísticas de ejemplo

Después de crear algunas autoridades y documentos, puedes consultar:

```bash
# Ver todas las autoridades y sus asignaciones
curl -X GET http://localhost:8000/admin/authorities \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Ver todos los documentos del sistema
curl -X GET http://localhost:8000/admin/documents \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Ver documentos de RURAL específicamente
curl -X GET "http://localhost:8000/authority/documents?instrument=RURAL" \
  -H "Authorization: Bearer $LEADER_TOKEN" | jq
```
