from flask import Blueprint, jsonify, request

from validators import (COMPUTER_SCHEMA, ApiError, get_json_body, new_id, query_bool,
                        query_float, validate_body, validate_id)
from . import deleted, repos

bp = Blueprint("computers", __name__, url_prefix="/computers")


def _get_or_404(id_computer):
    validate_id("computer", id_computer)
    doc = repos().computers.find_by_id(id_computer)
    if doc is None:
        raise ApiError(f"Computer '{id_computer}' not found", 404)
    return doc


def _load_components(ids):
    """Checks that every referenced component exists. Unknown ones -> 400."""
    found = repos().components.find_many_by_ids(ids)
    found_ids = {c["id_component"] for c in found}
    unknown = [i for i in ids if i not in found_ids]
    if unknown:
        raise ApiError(f"Unknown components: {unknown}", 400)
    return found


def _components_price(components):
    return round(sum(c["price_component"] for c in components), 2)


@bp.get("")
def list_computers():
    return jsonify(repos().computers.search(
        name=request.args.get("name"),
        min_price=query_float("min_price"),
        max_price=query_float("max_price"),
        in_stock=query_bool("in_stock"),
        expand=query_bool("expand"))), 200


@bp.get("/<id_computer>")
def get_computer(id_computer):
    _get_or_404(id_computer)
    return jsonify(repos().computers.find_by_id_expanded(id_computer)), 200


@bp.post("")
def create_computer():
    data = get_json_body()
    doc = validate_body(data, COMPUTER_SCHEMA)
    components = _load_components(doc["id_component"])
    doc.setdefault("price_computer", _components_price(components))
    id_computer = data.get("id_computer") or new_id("computer")
    validate_id("computer", id_computer)
    if repos().computers.exists(id_computer):
        raise ApiError(f"Computer '{id_computer}' already exists", 400)
    return jsonify(repos().computers.insert({"id_computer": id_computer, **doc})), 201


@bp.put("/<id_computer>")
def replace_computer(id_computer):
    _get_or_404(id_computer)
    doc = validate_body(get_json_body(), COMPUTER_SCHEMA)
    components = _load_components(doc["id_component"])
    doc.setdefault("price_computer", _components_price(components))
    return jsonify(repos().computers.replace(id_computer, {"id_computer": id_computer, **doc})), 200


@bp.patch("/<id_computer>")
def update_computer(id_computer):
    _get_or_404(id_computer)
    changes = validate_body(get_json_body(), COMPUTER_SCHEMA, partial=True)
    if "id_component" in changes:
        _load_components(changes["id_component"])
    return jsonify(repos().computers.update(id_computer, changes)), 200


@bp.delete("/<id_computer>")
def delete_computer(id_computer):
    _get_or_404(id_computer)
    if repos().sales.count_by_computer(id_computer):
        raise ApiError("Computer has sales registered, it cannot be deleted", 400)
    repos().computers.delete(id_computer)
    return jsonify(deleted("Computer", id_computer)), 200


@bp.post("/build")
def build_computer():
    """Custom build: {"id_component": [...]} -> total price and availability. Nothing is saved."""
    data = get_json_body()
    ids = validate_body({"id_component": data.get("id_component")},
                        {"id_component": COMPUTER_SCHEMA["id_component"]})["id_component"]
    components = _load_components(ids)
    out_of_stock = [c["id_component"] for c in components if c["stock_component"] <= 0]
    return jsonify({
        "components": components,
        "total_price": _components_price(components),
        "available": not out_of_stock,
        "out_of_stock": out_of_stock,
    }), 200
