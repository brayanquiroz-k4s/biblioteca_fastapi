"""
schemas.py
Esquemas Pydantic (v2) para validar las entradas y dar forma a las
salidas de la API de libros.

¿Por qué varios esquemas para un mismo recurso?
Cada operación necesita datos distintos:

  - LibroBase   → campos comunes y sus validaciones (titulo, autor, rating).
                  Es la fuente única de reglas: se definen una sola vez.
  - LibroCreate → lo que el cliente envía para CREAR un libro (POST).
                  Todos los campos son obligatorios y NO incluye `id`,
                  porque lo asigna MySQL automáticamente.
  - LibroUpdate → lo que el cliente envía para ACTUALIZAR (PUT).
                  Todos los campos son opcionales: se modifican solo
                  los que lleguen en el cuerpo de la petición.
  - LibroRead   → lo que la API DEVUELVE. Incluye `id` y sabe leer
                  directamente objetos SQLAlchemy (from_attributes).

Separarlos evita que el cliente pueda enviar campos que no le corresponden
(como `id`) y garantiza respuestas con una estructura predecible.
"""

from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# ---------------------------------------------------------------------------
# Tipos reutilizables con sus validaciones
# ---------------------------------------------------------------------------
# Annotated permite "adjuntar" reglas de validación a un tipo base.
# Se definen una sola vez y se reutilizan en todos los esquemas.

# Texto del título:
#   - strip_whitespace=True → elimina espacios al inicio y final,
#     así "   " se convierte en "" y falla el min_length.
#   - min_length=1          → no puede estar vacío.
#   - max_length=200        → coincide con String(200) del modelo SQLAlchemy.
TituloStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]

# Texto del autor: mismas reglas, longitud máxima según String(150) del modelo.
AutorStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]

# Calificación:
#   - ge=1, le=5   → entero entre 1 y 5 (inclusive).
#   - strict=True  → solo acepta enteros reales; rechaza "5" (texto) o 4.0 (decimal).
RatingInt = Annotated[int, Field(ge=1, le=5, strict=True)]


# ---------------------------------------------------------------------------
# Esquema base
# ---------------------------------------------------------------------------
class LibroBase(BaseModel):
    """Campos comunes de un libro con sus validaciones."""

    titulo: TituloStr = Field(
        description="Título del libro (no puede estar vacío).",
        examples=["Cien años de soledad"],
    )
    autor: AutorStr = Field(
        description="Autor del libro (no puede estar vacío).",
        examples=["Gabriel García Márquez"],
    )
    rating: RatingInt = Field(
        description="Calificación personal del libro, entero entre 1 y 5.",
        examples=[5],
    )


# ---------------------------------------------------------------------------
# Esquema de creación (entrada del POST)
# ---------------------------------------------------------------------------
class LibroCreate(LibroBase):
    """
    Datos requeridos para crear un libro.

    Hereda todos los campos obligatorios de LibroBase.
    extra="forbid" rechaza campos desconocidos (por ejemplo, si el cliente
    intenta enviar un `id`), devolviendo un error de validación claro.
    """

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Esquema de actualización (entrada del PUT)
# ---------------------------------------------------------------------------
class LibroUpdate(BaseModel):
    """
    Datos para actualizar un libro existente.

    Todos los campos son OPCIONALES: el cliente puede enviar solo los que
    quiere cambiar (por ejemplo, únicamente el rating) o todos a la vez.
    Las validaciones son las mismas que en LibroBase cuando el campo llega.

    No hereda de LibroBase porque allí los campos son obligatorios.
    """

    model_config = ConfigDict(extra="forbid")

    titulo: Optional[TituloStr] = Field(
        default=None,
        description="Nuevo título del libro.",
        examples=["El amor en los tiempos del cólera"],
    )
    autor: Optional[AutorStr] = Field(
        default=None,
        description="Nuevo autor del libro.",
        examples=["Gabriel García Márquez"],
    )
    rating: Optional[RatingInt] = Field(
        default=None,
        description="Nueva calificación, entero entre 1 y 5.",
        examples=[4],
    )

    @model_validator(mode="after")
    def validar_campos_enviados(self) -> "LibroUpdate":
        """
        Reglas extra para la actualización:
          1. El cuerpo no puede venir vacío ({}).
          2. Un campo enviado no puede ser null, porque en la base de datos
             titulo, autor y rating son obligatorios (NOT NULL).

        model_fields_set contiene solo los campos que el cliente envió
        explícitamente en el JSON.
        """
        if not self.model_fields_set:
            raise ValueError("Debes enviar al menos un campo para actualizar.")

        campos_nulos = [
            campo for campo in self.model_fields_set if getattr(self, campo) is None
        ]
        if campos_nulos:
            raise ValueError(
                f"Estos campos no pueden ser null: {', '.join(sorted(campos_nulos))}."
            )

        return self


# ---------------------------------------------------------------------------
# Esquema de lectura (salida de la API)
# ---------------------------------------------------------------------------
class LibroRead(LibroBase):
    """
    Representación de un libro en las respuestas de la API.

    from_attributes=True permite construir este esquema directamente desde
    un objeto SQLAlchemy (leyendo libro.id, libro.titulo, etc.), lo que
    FastAPI aprovecha al usar response_model=LibroRead.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador único del libro.", examples=[1])