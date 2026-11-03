"""Arranque de la API dentro de Docker. No modifica app.py."""
import logging

from app import create_app

logging.basicConfig(level=logging.INFO)
app = create_app()
for repo in vars(app.extensions["repos"]).values():
    repo.ensure_indexes()
app.run(host="0.0.0.0", port=5000)