"""Arranque de la API dentro de Docker. No modifica app.py."""
import logging

from app import create_app

def ensure_indexes(app):
    """Crea índices solo en repositorios que heredan BaseRepository."""
    repos = vars(app.extensions["repos"])
    for name in ("components", "computers", "sales"):
        repos[name].ensure_indexes()


logging.basicConfig(level=logging.INFO)
app = create_app()
ensure_indexes(app)
app.run(host="0.0.0.0", port=5000)