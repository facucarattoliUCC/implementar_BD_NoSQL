from flask import Blueprint, jsonify, request

from validators import (COMPONENT_SCHEMA, ApiError, get_json_body, new_id, query_bool,
                        query_float, validate_body, validate_id)
from . import deleted, repos

bp = Blueprint("components", __name__, url_prefix="/components")


def _get_or_404(id_component):
    validate_id("component", id_component)                        # 400
    doc = repos().components.find_by_id(id_component)
    if doc is None:
        raise ApiError(f"Component '{id_component}' not found", 404)  # 404
    return doc


@bp.get("")
def list_components():
    return jsonify(repos().components.search(
        name=request.args.get("name"),
        min_price=query_float("min_price"),
        max_price=query_float("max_price"),
        in_stock=query_bool("in_stock"))), 200


@bp.get("/<id_component>")
def get_component(id_component):
    return jsonify(_get_or_404(id_component)), 200


@bp.post("")
def create_component():
    data = get_json_body()
    doc = validate_body(data, COMPONENT_SCHEMA)
    id_component = data.get("id_component") or new_id("component")
    validate_id("component", id_component)
    if repos().components.exists(id_component):
        raise ApiError(f"Component '{id_component}' already exists", 400)
    return jsonify(repos().components.insert({"id_component": id_component, **doc})), 201


@bp.put("/<id_component>")
def replace_component(id_component):
    """PUT: full replacement, every field is required."""
    _get_or_404(id_component)
    doc = validate_body(get_json_body(), COMPONENT_SCHEMA)
    return jsonify(repos().components.replace(id_component, {"id_component": id_component, **doc})), 200


@bp.patch("/<id_component>")
def update_component(id_component):
    """PATCH: partial update, only the sent fields."""
    _get_or_404(id_component)
    changes = validate_body(get_json_body(), COMPONENT_SCHEMA, partial=True)
    return jsonify(repos().components.update(id_component, changes)), 200


@bp.delete("/<id_component>")
def delete_component(id_component):
    _get_or_404(id_component)
    used_by = repos().computers.count_using_component(id_component)
    if used_by:
        raise ApiError(f"Component is used by {used_by} computer(s), it cannot be deleted", 400)
    repos().components.delete(id_component)
    return jsonify(deleted("Component", id_component)), 200
