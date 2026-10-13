"""
models/libro.py
Modelo SQLAlchemy que representa la tabla `libros` de la Biblioteca Personal.

Usa el estilo moderno de SQLAlchemy 2.x (Mapped + mapped_column),
que combina las anotaciones de tipo de Python con la definición de columnas.
"""

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Libro(Base):
    """
    Representa un libro del catálogo personal.

    Cada instancia de esta clase corresponde a una fila de la tabla `libros`.
    """

    # Nombre real de la tabla en MySQL
    __tablename__ = "libros"

    # -----------------------------------------------------------------------
    # Restricciones a nivel de tabla
    # -----------------------------------------------------------------------
    # CheckConstraint crea una regla CHECK en MySQL (8.0.16+ la aplica)
    # para que la base de datos rechace ratings fuera del rango 1-5,
    # aunque alguien inserte datos sin pasar por la API.
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_libros_rating_rango"),
    )

    # -----------------------------------------------------------------------
    # Columnas
    # -----------------------------------------------------------------------

    # Llave primaria entera y autoincremental: MySQL asigna el valor
    # automáticamente al insertar (1, 2, 3...).
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Título del libro: obligatorio (NOT NULL), máximo 200 caracteres.
    # MySQL exige longitud en VARCHAR, por eso String(200).
    titulo: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    # Autor del libro: obligatorio (NOT NULL), máximo 150 caracteres.
    autor: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    # Calificación personal del libro: entero obligatorio entre 1 y 5.
    # El rango se garantiza con el CheckConstraint definido arriba
    # y, más adelante, también con las validaciones de Pydantic.
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    def __repr__(self) -> str:
        """Representación legible del objeto, útil al depurar en consola."""
        return (
            f"<Libro id={self.id} titulo='{self.titulo}' "
            f"autor='{self.autor}' rating={self.rating}>"
        )