"""
TechCore API - Flask + PyMongo, Repository pattern.

routes/        -> HTTP layer (validates input, returns status codes)
repositories/  -> data access layer (the only code that uses PyMongo)
validators.py  -> ID / body / query param validation
"""
import logging
import os
from types import SimpleNamespace

from flask import Flask, jsonify
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.exceptions import HTTPException

from repositories import ComponentRepository, ComputerRepository, SaleRepository
from routes import components, computers, reports, sales
from validators import ApiError


def get_db():
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"),
                         serverSelectionTimeoutMS=3000)
    return client[os.getenv("DB_NAME", "techcore")]


def register_error_handlers(app):
    def error(message, status):
        return jsonify({"error": message, "status": status}), status

    @app.errorhandler(ApiError)
    def api_error(e):                     # 400 / 404 raised by validators and routes
        return error(e.message, e.status)

    @app.errorhandler(DuplicateKeyError)
    def duplicate_key(e):                 # unique index violated
        return error("A document with that id already exists", 400)

    @app.errorhandler(HTTPException)
    def http_error(e):                    # unknown route (404), method not allowed (405)...
        return error(e.description, e.code)

    @app.errorhandler(PyMongoError)
    def database_error(e):                # Mongo down, timeout...
        app.logger.exception("Database error")
        return error("Database error", 500)

    @app.errorhandler(Exception)
    def unexpected_error(e):              # anything else
        app.logger.exception("Unexpected error")
        return error("Internal server error", 500)


def create_app(db=None):
    app = Flask(__name__)
    app.json.sort_keys = False

    db = db if db is not None else get_db()
    app.extensions["repos"] = SimpleNamespace(
        components=ComponentRepository(db),
        computers=ComputerRepository(db),
        sales=SaleRepository(db),
    )

    for bp in (components.bp, computers.bp, sales.bp, reports.bp):
        app.register_blueprint(bp)
    register_error_handlers(app)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    for repo in vars(app.extensions["repos"]).values():
        repo.ensure_indexes()
    app.run(debug=True, port=5000)
