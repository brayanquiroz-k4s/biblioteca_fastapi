"""
api/libros.py
Router con los endpoints REST del recurso Libro.

Responsabilidad de esta capa (solo lo relacionado con HTTP):
  - Definir rutas, métodos y códigos de estado.
  - Recibir la sesión de BD por inyección de dependencias (Depends).
  - Llamar a la capa de servicios.
  - Convertir los objetos SQLAlchemy en esquemas de respuesta (Pydantic).

La lógica de acceso a datos NO va aquí: está en services/libro_service.py.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import LibroCreate, LibroRead, LibroUpdate
from services.libro_service import (
    actualizar_libro,
    crear_libro,
    eliminar_libro,
    listar_libros,
    obtener_libro_por_id,
)

# ---------------------------------------------------------------------------
# Definición del router
# ---------------------------------------------------------------------------
# - prefix="/api/libros" → todas las rutas de este archivo empiezan así.
# - tags=["Libros"]      → agrupa los endpoints bajo la sección "Libros"
#                          en la documentación automática (/docs).
router = APIRouter(
    prefix="/api/libros",
    tags=["Libros"],
)


# ---------------------------------------------------------------------------
# GET /api/libros → Listar todos los libros
# ---------------------------------------------------------------------------
# La ruta es "" (cadena vacía) para que el endpoint quede exactamente en
# /api/libros, sin barra final. Si se usara "/", la URL sería /api/libros/
# y una petición a /api/libros recibiría una redirección 307.
#
# response_model=list[LibroRead] le indica a FastAPI:
#   - Cómo documentar la respuesta en /docs.
#   - Que filtre la salida para incluir solo los campos de LibroRead.
@router.get(
    "",
    response_model=list[LibroRead],
    summary="Listar libros",
    description="Devuelve todos los libros del catálogo, ordenados por id.",
)
def obtener_libros(db: Session = Depends(get_db)) -> list[LibroRead]:
    """
    Endpoint que lista todos los libros.

    `db` llega inyectada por FastAPI a través de Depends(get_db):
    se abre una sesión al iniciar la petición y se cierra al terminar.
    """
    # 1. Obtener los objetos SQLAlchemy desde la capa de servicios
    libros = listar_libros(db)

    # 2. Convertir cada objeto Libro (SQLAlchemy) a LibroRead (Pydantic).
    #    model_validate funciona gracias a from_attributes=True en LibroRead,
    #    que le permite leer atributos (libro.id, libro.titulo...) del objeto.
    return [LibroRead.model_validate(libro) for libro in libros]


# ---------------------------------------------------------------------------
# POST /api/libros → Crear un libro
# ---------------------------------------------------------------------------
# - El parámetro `datos: LibroCreate` le indica a FastAPI que debe leer el
#   cuerpo (body) de la petición como JSON y validarlo con LibroCreate.
#   Si la validación falla, FastAPI responde 422 automáticamente y esta
#   función ni siquiera se ejecuta.
# - status_code=201 (Created) es el código REST estándar cuando se crea
#   un recurso nuevo (en lugar del 200 por defecto).
# - response_model=LibroRead define la forma de la respuesta: el libro
#   creado, ahora con su `id`.
@router.post(
    "",
    response_model=LibroRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear libro",
    description="Registra un nuevo libro en el catálogo y lo devuelve con su id asignado.",
)
def agregar_libro(datos: LibroCreate, db: Session = Depends(get_db)) -> LibroRead:
    """
    Endpoint que crea un nuevo libro.

    `datos` llega ya validado por Pydantic (titulo y autor no vacíos,
    rating entero entre 1 y 5, sin campos extra).
    """
    # 1. Delegar la creación a la capa de servicios
    libro = crear_libro(db, datos)

    # 2. Convertir el objeto SQLAlchemy persistido al esquema de respuesta
    return LibroRead.model_validate(libro)


# ---------------------------------------------------------------------------
# GET /api/libros/{id} → Obtener un libro por su id
# ---------------------------------------------------------------------------
# - "{id}" en la ruta es un parámetro de ruta (path parameter): el valor
#   se toma de la URL, por ejemplo /api/libros/3 → id = 3.
# - Path(ge=1) valida que sea un entero mayor o igual a 1. Si llega
#   "abc" o 0, FastAPI responde 422 sin ejecutar la función.
# - responses={404: ...} documenta en /docs que este endpoint puede
#   responder 404 cuando el libro no existe.
@router.get(
    "/{id}",
    response_model=LibroRead,
    summary="Obtener libro por id",
    description="Devuelve un libro específico según su id. Responde 404 si no existe.",
    responses={404: {"description": "Libro no encontrado"}},
)
def obtener_libro(
    id: Annotated[int, Path(ge=1, description="Id del libro a consultar.")],
    db: Session = Depends(get_db),
) -> LibroRead:
    """
    Endpoint que consulta un libro por su id.

    Si el servicio devuelve None, se lanza HTTPException con 404;
    FastAPI la convierte en una respuesta JSON: {"detail": "..."}.
    """
    # 1. Buscar el libro en la capa de servicios
    libro = obtener_libro_por_id(db, id)

    # 2. Traducir "no encontrado" (None) al código HTTP correspondiente
    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un libro con id {id}.",
        )

    # 3. Convertir el objeto SQLAlchemy al esquema de respuesta
    return LibroRead.model_validate(libro)


# ---------------------------------------------------------------------------
# PUT /api/libros/{id} → Actualizar un libro
# ---------------------------------------------------------------------------
# Este endpoint recibe información de dos lugares:
#   - id    → de la URL (parámetro de ruta), validado con Path(ge=1).
#   - datos → del cuerpo JSON, validado con LibroUpdate:
#             campos opcionales, sin null explícitos, sin cuerpo vacío
#             y sin campos extra.
#
# Respuestas posibles:
#   - 200 → libro actualizado (esquema LibroRead).
#   - 404 → no existe un libro con ese id.
#   - 422 → id inválido o cuerpo que no cumple las validaciones.
@router.put(
    "/{id}",
    response_model=LibroRead,
    summary="Actualizar libro",
    description=(
        "Actualiza un libro existente. Se pueden enviar todos los campos "
        "o solo los que se desean modificar. Responde 404 si no existe."
    ),
    responses={404: {"description": "Libro no encontrado"}},
)
def editar_libro(
    id: Annotated[int, Path(ge=1, description="Id del libro a actualizar.")],
    datos: LibroUpdate,
    db: Session = Depends(get_db),
) -> LibroRead:
    """
    Endpoint que actualiza un libro.

    Devuelve el recurso completo ya actualizado, para que el cliente
    tenga el estado final sin necesidad de hacer otra consulta.
    """
    # 1. Delegar la actualización a la capa de servicios
    libro = actualizar_libro(db, id, datos)

    # 2. Si el servicio devuelve None, el libro no existe → 404
    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un libro con id {id}.",
        )

    # 3. Convertir el objeto actualizado al esquema de respuesta
    return LibroRead.model_validate(libro)



# ---------------------------------------------------------------------------
# DELETE /api/libros/{id} → Eliminar un libro
# ---------------------------------------------------------------------------
# - status_code=204 (No Content): el borrado fue exitoso y la respuesta
#   NO lleva cuerpo. Es el código REST más común para un DELETE exitoso.
# - No se declara response_model porque no se devuelve ningún dato.
# - La función retorna None; FastAPI envía la respuesta 204 vacía.
#
# Respuestas posibles:
#   - 204 → libro eliminado (sin cuerpo).
#   - 404 → no existe un libro con ese id.
#   - 422 → id inválido (texto, 0 o negativo).
@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar libro",
    description="Elimina un libro del catálogo. Responde 204 sin contenido si se eliminó y 404 si no existe.",
    responses={404: {"description": "Libro no encontrado"}},
)
def borrar_libro(
    id: Annotated[int, Path(ge=1, description="Id del libro a eliminar.")],
    db: Session = Depends(get_db),
) -> None:
    """
    Endpoint que elimina un libro.

    El servicio devuelve True si eliminó el libro y False si no existía.
    """
    # 1. Delegar el borrado a la capa de servicios
    eliminado = eliminar_libro(db, id)

    # 2. Si no se eliminó porque no existía → 404
    if not eliminado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un libro con id {id}.",
        )

    # 3. Éxito: no se devuelve contenido (204 No Content)
    return None