"""
main.py
Punto de entrada de la API REST de la Biblioteca Personal.

Aquí se crea la instancia principal de FastAPI, se configura CORS
y se registran los routers de la aplicación.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importar el router con los endpoints de libros
from api.libros import router as libros_router

# ---------------------------------------------------------------------------
# Instancia principal de la aplicación
# ---------------------------------------------------------------------------
# `app` es el objeto central de FastAPI: registra todas las rutas,
# middlewares y configuraciones de la API. Uvicorn lo busca por su nombre
# cuando ejecutamos `uvicorn main:app` (archivo main.py, variable app).
#
# Los parámetros title, description y version se muestran en la
# documentación automática (/docs y /redoc).
app = FastAPI(
    title="API Biblioteca Personal",
    description="Backend REST para administrar un catálogo personal de libros.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Configuración de CORS (Cross-Origin Resource Sharing)
# ---------------------------------------------------------------------------
# Lista de orígenes (protocolo + host + puerto) a los que el navegador
# les permitirá consumir esta API. Se incluyen localhost y 127.0.0.1
# porque para el navegador son orígenes distintos.
ORIGENES_PERMITIDOS = [
    "http://localhost:4200",   # Angular (ng serve)
    "http://127.0.0.1:4200",
    "http://localhost:5173",   # React con Vite (npm run dev)
    "http://127.0.0.1:5173",
]


# CORSMiddleware intercepta cada petición y agrega las cabeceras
# Access-Control-Allow-* que el navegador necesita. También responde
# automáticamente las peticiones de verificación previa (preflight OPTIONS).
app.add_middleware(
    CORSMiddleware,
    # Solo estos orígenes pueden consumir la API desde el navegador.
    allow_origins=ORIGENES_PERMITIDOS,
    # Métodos HTTP que usa el CRUD de libros (OPTIONS es el preflight).
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    # Cabeceras que el frontend puede enviar (por ejemplo, Content-Type: application/json).
    allow_headers=["*"],
    # No se envían cookies ni credenciales: esta API no tiene autenticación.
    # Si en el futuro se agregan cookies de sesión, se cambia a True
    # (y en ese caso allow_origins nunca debe ser ["*"]).
    allow_credentials=False,
)

# Registrar el router de libros en la aplicación.
# Todas sus rutas quedan disponibles bajo el prefijo /api/libros.
app.include_router(libros_router)


# ---------------------------------------------------------------------------
# Endpoint de prueba (health check)
# ---------------------------------------------------------------------------
# Responde a peticiones GET en la raíz "/".
# Sirve para comprobar rápidamente que la API está levantada y respondiendo.
# FastAPI convierte automáticamente el diccionario retornado en JSON.
@app.get("/", tags=["Estado"])
def raiz():
    """Verifica que la API está activa."""
    return {
        "mensaje": "API Biblioteca Personal funcionando correctamente 📚",
        "estado": "activo",
    }