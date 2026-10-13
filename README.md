# 📚 API Biblioteca Personal

API REST con **FastAPI** y **MySQL** para administrar un catálogo personal de libros (CRUD completo).

## Tecnologías
FastAPI · Uvicorn · SQLAlchemy 2 · Alembic · Pydantic v2 · MySQL · PyMySQL

## Estructura
```
api/        → routers (endpoints HTTP)
services/   → lógica de acceso a datos
models/     → modelos SQLAlchemy
schemas.py  → esquemas Pydantic
alembic/    → migraciones
```

## Instalación
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

1. Crear la base de datos `biblioteca_db` en MySQL.
2. Copiar `.env.example` como `.env` y completar las credenciales.
3. Aplicar migraciones: `python migrate.py`
4. Ejecutar: `uvicorn main:app --reload --port 8080`

## Endpoints
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/libros` | Listar libros |
| POST | `/api/libros` | Crear libro |
| GET | `/api/libros/{id}` | Obtener libro |
| PUT | `/api/libros/{id}` | Actualizar libro (total o parcial) |
| DELETE | `/api/libros/{id}` | Eliminar libro |

Documentación interactiva: `http://localhost:8080/docs`