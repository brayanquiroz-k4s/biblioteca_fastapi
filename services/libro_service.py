"""
services/libro_service.py
Capa de servicios para el recurso Libro.

¿Por qué una capa de servicios?
  - Separa la lógica de acceso a datos de los endpoints HTTP.
  - Los endpoints quedan cortos: reciben la petición, llaman al servicio
    y devuelven la respuesta.
  - Las funciones de servicio se pueden reutilizar (desde otros endpoints,
    scripts o pruebas) sin depender de FastAPI.

Cada función recibe la sesión de base de datos (`db`) como parámetro.
Quien la llama (el endpoint, mediante Depends(get_db)) es responsable
de abrirla y cerrarla.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import Libro
from schemas import LibroCreate, LibroUpdate


def listar_libros(db: Session) -> list[Libro]:
    """
    Devuelve todos los libros registrados en la tabla `libros`,
    ordenados por id de forma ascendente.

    Parámetros:
        db: sesión activa de SQLAlchemy.

    Retorna:
        Lista de objetos Libro (lista vacía si no hay registros).
    """
    # Construye la consulta con el estilo de SQLAlchemy 2.x:
    # equivale a: SELECT * FROM libros ORDER BY id ASC
    consulta = select(Libro).order_by(Libro.id)

    # db.scalars() ejecuta la consulta y devuelve directamente objetos Libro
    # (no tuplas); .all() los materializa en una lista.
    return list(db.scalars(consulta).all())


def crear_libro(db: Session, datos: LibroCreate) -> Libro:
    """
    Crea un nuevo libro en la base de datos y lo devuelve ya persistido.

    Flujo:
      1. Convertir el esquema Pydantic (LibroCreate) en un diccionario.
      2. Construir con ese diccionario una instancia del modelo SQLAlchemy.
      3. Agregarla a la sesión y confirmar la transacción (commit).
      4. Refrescar el objeto para obtener los valores generados por MySQL
         (en este caso, el `id` autoincremental).

    Parámetros:
        db:    sesión activa de SQLAlchemy.
        datos: datos del libro ya validados por Pydantic.

    Retorna:
        El objeto Libro guardado, incluyendo su `id`.
    """
    # 1-2. model_dump() devuelve {"titulo": ..., "autor": ..., "rating": ...}
    #      y el operador ** lo desempaqueta como argumentos con nombre:
    #      Libro(titulo=..., autor=..., rating=...)
    nuevo_libro = Libro(**datos.model_dump())

    try:
        # 3. add() marca el objeto como pendiente de insertar;
        #    commit() ejecuta el INSERT y confirma la transacción.
        db.add(nuevo_libro)
        db.commit()
    except SQLAlchemyError:
        # Si el INSERT falla (por ejemplo, se viola el CHECK del rating
        # o se pierde la conexión), se deshace la transacción para dejar
        # la sesión en un estado limpio, y se relanza el error.
        db.rollback()
        raise

    # 4. refresh() vuelve a leer el registro desde MySQL y completa
    #    los atributos generados por la base de datos (el id).
    db.refresh(nuevo_libro)

    return nuevo_libro


def obtener_libro_por_id(db: Session, id: int) -> Optional[Libro]:
    """
    Busca un libro por su llave primaria.

    Parámetros:
        db: sesión activa de SQLAlchemy.
        id: identificador del libro a buscar.

    Retorna:
        El objeto Libro si existe, o None si no hay ningún libro con ese id.

    Nota:
        Esta función NO lanza errores HTTP. Devolver None deja la decisión
        al llamador: el router responderá 404, pero otro uso (un script,
        una prueba) podría manejar el caso de otra forma.
    """
    # db.get() está optimizado para búsquedas por llave primaria:
    #   - Primero revisa si el objeto ya está cargado en la sesión
    #     (identity map); si es así, lo devuelve sin consultar MySQL.
    #   - Si no, ejecuta: SELECT * FROM libros WHERE id = :id
    #   - Si no encuentra el registro, devuelve None.
    return db.get(Libro, id)


def actualizar_libro(db: Session, id: int, datos: LibroUpdate) -> Optional[Libro]:
    """
    Actualiza un libro existente con los campos recibidos.

    Soporta actualización parcial: solo se modifican los campos que el
    cliente envió explícitamente. Los demás conservan su valor actual.

    Flujo:
      1. Buscar el libro por id (reutilizando obtener_libro_por_id).
      2. Si no existe, devolver None (el router responderá 404).
      3. Extraer solo los campos enviados por el cliente.
      4. Asignarlos uno por uno al objeto SQLAlchemy.
      5. Confirmar la transacción y refrescar el objeto.

    Parámetros:
        db:    sesión activa de SQLAlchemy.
        id:    identificador del libro a actualizar.
        datos: campos a modificar, ya validados por Pydantic.

    Retorna:
        El objeto Libro actualizado, o None si no existe.
    """
    # 1. Localizar el libro
    libro = obtener_libro_por_id(db, id)

    # 2. Caso "no encontrado": no hay nada que actualizar
    if libro is None:
        return None

    # 3. exclude_unset=True devuelve SOLO los campos que llegaron en el JSON.
    #    Ejemplo: si el cliente envía {"rating": 3}, cambios = {"rating": 3}
    #    y titulo/autor no se tocan. Sin exclude_unset, los campos no
    #    enviados vendrían como None y borrarían los valores existentes.
    cambios = datos.model_dump(exclude_unset=True)

    # 4. setattr(objeto, "campo", valor) equivale a: libro.campo = valor.
    #    SQLAlchemy detecta qué atributos cambiaron y en el commit genera
    #    un UPDATE solo con esas columnas.
    for campo, valor in cambios.items():
        setattr(libro, campo, valor)

    try:
        # 5. Ejecutar el UPDATE y confirmar la transacción
        db.commit()
    except SQLAlchemyError:
        # Si falla, deshacer los cambios para dejar la sesión limpia
        db.rollback()
        raise

    # Releer el registro desde MySQL para devolver el estado definitivo
    db.refresh(libro)

    return libro



def eliminar_libro(db: Session, id: int) -> bool:
    """
    Elimina físicamente un libro de la base de datos.

    Flujo:
      1. Buscar el libro por id (reutilizando obtener_libro_por_id).
      2. Si no existe, devolver False (el router responderá 404).
      3. Marcarlo para eliminación y confirmar la transacción.

    Parámetros:
        db: sesión activa de SQLAlchemy.
        id: identificador del libro a eliminar.

    Retorna:
        True si el libro existía y se eliminó; False si no se encontró.

    ¿Por qué un booleano y no el objeto?
        Después del borrado el registro ya no existe en la base de datos,
        así que no hay un recurso "actual" que devolver. El booleano basta
        para que el router distinga entre éxito y "no encontrado".
    """
    # 1. Localizar el libro
    libro = obtener_libro_por_id(db, id)

    # 2. Caso "no encontrado": no hay nada que eliminar
    if libro is None:
        return False

    try:
        # 3. delete() marca el objeto para eliminación;
        #    commit() ejecuta: DELETE FROM libros WHERE id = :id
        db.delete(libro)
        db.commit()
    except SQLAlchemyError:
        # Si falla, deshacer para dejar la sesión en un estado limpio
        db.rollback()
        raise

    return True