from flask import Blueprint, jsonify, request
from datetime import datetime, timezone

from validators import (CLIENT_SCHEMA, SALE_SCHEMA, SELLER_SCHEMA, ApiError, get_json_body,
                        new_id, validate_body, validate_embedded, validate_id)
from . import deleted, repos

bp = Blueprint("sales", __name__, url_prefix="/sales")


def _get_or_404(id_sale):
    validate_id("sale", id_sale)
    doc = repos().sales.find_by_id(id_sale)
    if doc is None:
        raise ApiError(f"Sale '{id_sale}' not found", 404)
    return doc


def _validate_sale(data, partial=False):
    clean = validate_body(data, SALE_SCHEMA, partial=partial)
    if "Client" in clean:
        clean["Client"] = validate_embedded(clean["Client"], CLIENT_SCHEMA, "Client")
    if "Seller" in clean:
        clean["Seller"] = validate_embedded(clean["Seller"], SELLER_SCHEMA, "Seller")
    return clean


def _take_stock(id_computer, quantity):
    """Decrements stock atomically. 404 if the computer doesn't exist, 400 if not enough stock."""
    computer = repos().computers.decrement_stock(id_computer, quantity)
    if computer is None:
        if not repos().computers.exists(id_computer):
            raise ApiError(f"Computer '{id_computer}' not found", 404)
        raise ApiError(f"Not enough stock for computer '{id_computer}'", 400)
    return computer


def _move_stock(old_sale, new_computer, new_quantity):
    """When a sale changes computer/quantity: returns the old units and takes the new ones.
    If there's not enough stock, rolls back and raises."""
    old_computer, old_quantity = old_sale["id_computer"], old_sale.get("quantity", 1)
    repos().computers.increment_stock(old_computer, old_quantity)
    try:
        return _take_stock(new_computer, new_quantity)
    except ApiError:
        repos().computers.decrement_stock(old_computer, old_quantity)  # rollback
        raise


@bp.get("")
def list_sales():
    filters = {"id_client": ("client", request.args.get("client")),
               "id_seller": ("seller", request.args.get("seller")),
               "id_computer": ("computer", request.args.get("computer"))}
    for entity, value in filters.values():
        if value is not None:
            validate_id(entity, value)
    return jsonify(repos().sales.search(**{k: v for k, (_, v) in filters.items()})), 200


@bp.get("/<id_sale>")
def get_sale(id_sale):
    return jsonify(_get_or_404(id_sale)), 200


@bp.post("")
def create_sale():
    """Body: {id_computer, quantity (default 1), Client: {...}, Seller: {...}}"""
    sale = _validate_sale(get_json_body())
    quantity = sale.get("quantity", 1)
    computer = _take_stock(sale["id_computer"], quantity)
    doc = {"id_sale": new_id("sale"),
           "id_computer": sale["id_computer"],
           "quantity": quantity,
           "amount": round(computer["price_computer"] * quantity, 2),
           "date": datetime.now(timezone.utc).isoformat(),
           "Client": sale["Client"],
           "Seller": sale["Seller"]}
    return jsonify(repos().sales.insert(doc)), 201


def _update(id_sale, partial):
    old = _get_or_404(id_sale)
    changes = _validate_sale(get_json_body(), partial=partial)
    new_computer = changes.get("id_computer", old["id_computer"])
    new_quantity = changes.get("quantity", old.get("quantity", 1) if partial else 1)

    if new_computer != old["id_computer"] or new_quantity != old.get("quantity", 1):
        computer = _move_stock(old, new_computer, new_quantity)
        changes["id_computer"], changes["quantity"] = new_computer, new_quantity
        changes["amount"] = round(computer["price_computer"] * new_quantity, 2)

    if partial:
        return repos().sales.update(id_sale, changes)
    # PUT keeps the system fields (id, amount, date) and replaces the rest
    doc = {"id_sale": id_sale, "id_computer": new_computer, "quantity": new_quantity,
           "amount": changes.get("amount", old["amount"]), "date": old["date"],
           "Client": changes["Client"], "Seller": changes["Seller"]}
    return repos().sales.replace(id_sale, doc)


@bp.put("/<id_sale>")
def replace_sale(id_sale):
    return jsonify(_update(id_sale, partial=False)), 200


@bp.patch("/<id_sale>")
def update_sale(id_sale):
    return jsonify(_update(id_sale, partial=True)), 200


@bp.delete("/<id_sale>")
def delete_sale(id_sale):
    """Cancels the sale and returns the units to stock."""
    sale = _get_or_404(id_sale)
    repos().sales.delete(id_sale)
    repos().computers.increment_stock(sale["id_computer"], sale.get("quantity", 1))
    return jsonify(deleted("Sale", id_sale)), 200
