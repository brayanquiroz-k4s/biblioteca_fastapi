"""
migrate.py
Automatiza el flujo completo de migraciones con Alembic.

Pasos que ejecuta:
  1. Carga el .env (a través de database.py) y configura Alembic con esa URL.
  2. Detecta y limpia registros huérfanos en la tabla `alembic_version`
     (versiones que existen en la BD pero cuyo archivo ya no está en
     alembic/versions, por ejemplo si se borró la carpeta).
  3. Aplica las migraciones existentes que estén pendientes.
  4. Compara los modelos con la BD; si hay cambios, genera una revisión
     autogenerada y la aplica (upgrade head).

Uso:
  python migrate.py                          -> mensaje por defecto
  python migrate.py "crear tabla libros"     -> mensaje personalizado
"""

import sys

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util import CommandError
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

# Importar models registra la clase Libro en Base.metadata
import models  # noqa: F401
from alembic import command

# Importar database ejecuta load_dotenv() y construye DATABASE_URL desde .env
from database import DATABASE_URL, Base, engine

ALEMBIC_INI = "alembic.ini"
TABLA_VERSIONES = "alembic_version"


def crear_config_alembic() -> Config:
    """
    Carga alembic.ini y sobrescribe sqlalchemy.url con la URL del .env.

    alembic.ini se lee con ConfigParser, donde '%' es un carácter especial;
    por eso se duplica ('%%') para soportar contraseñas con caracteres
    especiales codificados (por ejemplo '@' -> '%40').
    """
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))
    return cfg


def limpiar_version_huerfana(cfg: Config) -> None:
    """
    Elimina de `alembic_version` las revisiones que no tienen archivo
    correspondiente en alembic/versions.

    Si no se limpian, Alembic falla con:
    "Can't locate revision identified by '...'".
    """
    script = ScriptDirectory.from_config(cfg)
    revisiones_conocidas = {rev.revision for rev in script.walk_revisions()}

    # engine.begin() abre una transacción que hace commit automático al salir
    with engine.begin() as conn:
        if not inspect(conn).has_table(TABLA_VERSIONES):
            print(f"   ℹ️  La tabla '{TABLA_VERSIONES}' aún no existe (primera migración).")
            return

        versiones_en_bd = [
            fila[0]
            for fila in conn.execute(text(f"SELECT version_num FROM {TABLA_VERSIONES}"))
        ]
        huerfanas = [v for v in versiones_en_bd if v not in revisiones_conocidas]

        if not huerfanas:
            print("   ✅ Sin versiones huérfanas.")
            return

        for version in huerfanas:
            conn.execute(
                text(f"DELETE FROM {TABLA_VERSIONES} WHERE version_num = :v"),
                {"v": version},
            )
        print(f"   🧹 Versiones huérfanas eliminadas: {', '.join(huerfanas)}")


def detectar_cambios() -> list:
    """
    Compara Base.metadata (modelos Python) con el esquema real de MySQL.
    Devuelve la lista de diferencias; vacía si todo está sincronizado.
    """
    with engine.connect() as conn:
        contexto = MigrationContext.configure(conn)
        return compare_metadata(contexto, Base.metadata)


def main() -> None:
    """Orquesta el flujo completo de migración."""
    mensaje = sys.argv[1] if len(sys.argv) > 1 else "migracion automatica"

    try:
        cfg = crear_config_alembic()

        print("1️⃣  Revisando versiones huérfanas en la base de datos...")
        limpiar_version_huerfana(cfg)

        print("2️⃣  Aplicando migraciones existentes pendientes...")
        command.upgrade(cfg, "head")

        print("3️⃣  Comparando modelos con la base de datos...")
        diferencias = detectar_cambios()

        if not diferencias:
            print("   ✅ La base de datos ya está sincronizada con los modelos. Nada que migrar.")
            return

        print(f"   🔍 Cambios detectados: {len(diferencias)}")

        print(f"4️⃣  Generando revisión autogenerada: '{mensaje}'...")
        command.revision(cfg, message=mensaje, autogenerate=True)

        print("5️⃣  Aplicando la nueva migración (upgrade head)...")
        command.upgrade(cfg, "head")

        print("🎉 Migración completada correctamente.")

    except SQLAlchemyError as error:
        print(f"❌ Error de base de datos: {error}")
        sys.exit(1)
    except CommandError as error:
        print(f"❌ Error de Alembic: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()