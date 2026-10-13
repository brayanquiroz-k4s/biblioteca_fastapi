"""
tests/test_libros.py
Pruebas de los endpoints de libros.

Usan una base SQLite en memoria en lugar de MySQL: get_db se reemplaza
con dependency_overrides, así las pruebas no tocan la base real y cada
prueba arranca con la tabla vacía.

Ejecutar desde la raíz del proyecto:
    pytest -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models  # noqa: F401  (registra Libro en Base.metadata)
from database import Base, get_db
from main import app

# StaticPool reutiliza una única conexión: necesario para que la base
# en memoria sea la misma en todas las sesiones de una prueba.
engine_pruebas = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SesionPruebas = sessionmaker(bind=engine_pruebas, autocommit=False, autoflush=False)


def get_db_pruebas():
    db = SesionPruebas()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Crea las tablas, entrega un cliente HTTP y las borra al terminar."""
    Base.metadata.create_all(engine_pruebas)
    app.dependency_overrides[get_db] = get_db_pruebas
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine_pruebas)


LIBRO = {"titulo": "Cien años de soledad", "autor": "Gabriel García Márquez", "rating": 5}


def crear(client, **cambios):
    return client.post("/api/libros", json={**LIBRO, **cambios})


# --- Crear ------------------------------------------------------------------

def test_crear_libro(client):
    r = crear(client)
    assert r.status_code == 201
    assert r.json() == {"id": 1, **LIBRO}


@pytest.mark.parametrize(
    "cambios",
    [
        {"rating": 0},
        {"rating": 6},
        {"rating": "5"},      # strict: no acepta texto
        {"titulo": "   "},    # solo espacios
        {"autor": ""},
        {"id": 99},           # campo extra prohibido
    ],
)
def test_crear_libro_invalido(client, cambios):
    assert crear(client, **cambios).status_code == 422


# --- Listar y obtener -------------------------------------------------------

def test_listar_vacio(client):
    r = client.get("/api/libros")
    assert r.status_code == 200
    assert r.json() == []


def test_listar_ordenado_por_id(client):
    crear(client, titulo="A")
    crear(client, titulo="B")
    titulos = [l["titulo"] for l in client.get("/api/libros").json()]
    assert titulos == ["A", "B"]


def test_obtener_libro(client):
    crear(client)
    r = client.get("/api/libros/1")
    assert r.status_code == 200
    assert r.json()["titulo"] == LIBRO["titulo"]


def test_obtener_libro_inexistente(client):
    assert client.get("/api/libros/999").status_code == 404


def test_obtener_id_invalido(client):
    assert client.get("/api/libros/0").status_code == 422


# --- Actualizar -------------------------------------------------------------

def test_actualizar_parcial(client):
    crear(client)
    r = client.put("/api/libros/1", json={"rating": 3})
    assert r.status_code == 200
    assert r.json() == {"id": 1, **LIBRO, "rating": 3}


@pytest.mark.parametrize("cuerpo", [{}, {"titulo": None}, {"rating": 9}])
def test_actualizar_invalido(client, cuerpo):
    crear(client)
    assert client.put("/api/libros/1", json=cuerpo).status_code == 422


def test_actualizar_inexistente(client):
    assert client.put("/api/libros/999", json={"rating": 3}).status_code == 404


# --- Eliminar ---------------------------------------------------------------

def test_eliminar_libro(client):
    crear(client)
    r = client.delete("/api/libros/1")
    assert r.status_code == 204
    assert r.content == b""
    assert client.get("/api/libros/1").status_code == 404


def test_eliminar_inexistente(client):
    assert client.delete("/api/libros/999").status_code == 404
