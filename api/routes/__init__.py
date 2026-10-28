from flask import current_app


def repos():
    """Repositories registered in create_app()."""
    return current_app.extensions["repos"]


def deleted(entity, id_):
    return {"message": f"{entity} deleted", "id": id_}
