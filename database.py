"""
database.py
Configuración central de la conexión a MySQL con SQLAlchemy.

Este módulo expone:
- engine       → motor de conexión a la base de datos.
- SessionLocal → fábrica para crear sesiones de BD.
- Base         → clase base de la que heredarán todos los modelos.
- get_db()     → dependencia de FastAPI que entrega una sesión por petición.

También puede ejecutarse directamente (python database.py)
para comprobar que la conexión a MySQL funciona.
"""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# 1. Cargar variables de entorno
# ---------------------------------------------------------------------------
# load_dotenv() lee el archivo .env de la carpeta del proyecto y deja sus
# valores disponibles en os.environ. Así las credenciales no quedan
# escritas en el código fuente.
load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "biblioteca_db")

# ---------------------------------------------------------------------------
# 2. Construir la URL de conexión
# ---------------------------------------------------------------------------
# Formato: mysql+pymysql://usuario:password@host:puerto/base_de_datos
#   - mysql   → dialecto (tipo de base de datos)
#   - pymysql → driver que usa SQLAlchemy para comunicarse con MySQL
#
# quote_plus() escapa caracteres especiales de la contraseña (@, :, /, #...)
# para que no rompan la URL.
# charset=utf8mb4 asegura soporte completo de caracteres (tildes, ñ, emojis).
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

# ---------------------------------------------------------------------------
# 3. Crear el engine
# ---------------------------------------------------------------------------
# El engine administra el pool de conexiones hacia MySQL.
#   - echo=False         → no imprime cada SQL generado (cámbialo a True
#                          si quieres ver las consultas en consola).
#   - pool_pre_ping=True → verifica que la conexión siga viva antes de usarla;
#                          evita errores cuando MySQL cierra conexiones inactivas.
engine = create_engine(
    DATABASE_URL,
    echo=False, # Cambiar a True para visual en la terminal las consultas
    pool_pre_ping=True,
)

# ---------------------------------------------------------------------------
# 4. Fábrica de sesiones
# ---------------------------------------------------------------------------
# SessionLocal() crea una nueva sesión cada vez que se llama.
# Una sesión es la "unidad de trabajo" con la BD: agrupa consultas,
# inserciones y actualizaciones hasta que se hace commit.
#   - autocommit=False → los cambios se confirman explícitamente con commit().
#   - autoflush=False  → no envía cambios pendientes a la BD automáticamente
#                        antes de cada consulta; tenemos control explícito.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# 5. Clase base para los modelos
# ---------------------------------------------------------------------------
# Todos los modelos (tablas) heredarán de Base. SQLAlchemy registra en
# Base.metadata la información de cada tabla, que luego usará Alembic
# para generar las migraciones.
Base = declarative_base()


# ---------------------------------------------------------------------------
# 6. Dependencia de FastAPI: una sesión por petición
# ---------------------------------------------------------------------------
def get_db():
    """
    Entrega una sesión de base de datos a cada endpoint que la solicite
    mediante Depends(get_db).

    - Abre la sesión al inicio de la petición.
    - La entrega al endpoint con `yield`.
    - La cierra SIEMPRE al terminar (finally), incluso si hubo errores,
      devolviendo la conexión al pool.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 7. Prueba rápida de conexión
# ---------------------------------------------------------------------------
# Este bloque solo se ejecuta al correr `python database.py` directamente.
# No se ejecuta cuando otro archivo importa este módulo.
if __name__ == "__main__":
    print(f"🔌 Intentando conectar a MySQL en {DB_HOST}:{DB_PORT}/{DB_NAME} ...")
    try:
        # Abrir y cerrar una conexión es suficiente para validar
        # credenciales, host, puerto y existencia de la base de datos.
        with engine.connect():
            print("✅ Conexión exitosa a la base de datos MySQL.")
    except SQLAlchemyError as error:
        print("❌ Error al conectar con la base de datos:")
        print(f"   {error}")