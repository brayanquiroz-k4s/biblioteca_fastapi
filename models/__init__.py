"""
models/__init__.py
Convierte la carpeta `models` en un paquete de Python y centraliza
la importación de todos los modelos del proyecto.

Al importar `models`, se cargan todas las clases listadas aquí y quedan
registradas en Base.metadata. Esto será clave cuando Alembic necesite
detectar las tablas para generar migraciones.
"""

from models.libro import Libro

# Lista explícita de lo que exporta el paquete
__all__ = ["Libro"]