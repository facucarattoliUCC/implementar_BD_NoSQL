"""Read-only reports. Every endpoint returns a flat JSON (list of rows or a dict)
so it can be loaded directly into a pandas DataFrame:  pd.DataFrame(requests.get(url).json())"""
from flask import Blueprint, jsonify

from validators import query_int
from . import repos

bp = Blueprint("reports", __name__)


@bp.get("/stock/low")
def low_stock():
    threshold = query_int("threshold", default=5)
    return jsonify({
        "threshold": threshold,
        "components": repos().components.low_stock(threshold),
        "computers": repos().computers.low_stock(threshold),
    }), 200


# ---------------------------------------------------------------- sales
@bp.get("/reports/summary")
def summary():
    return jsonify(repos().reports.summary()), 200


@bp.get("/reports/sales-by-month")
def sales_by_month():
    return jsonify(repos().reports.sales_by_month()), 200


@bp.get("/reports/sellers")
def sales_by_seller():
    return jsonify(repos().reports.sales_by_seller()), 200


@bp.get("/reports/top-computers")
def top_computers():
    return jsonify(repos().reports.top_computers(query_int("limit", default=5, minimum=1))), 200


@bp.get("/reports/top-clients")
def top_clients():
    return jsonify(repos().reports.top_clients(query_int("limit", default=10, minimum=1))), 200


@bp.get("/reports/sales-by-line")
def sales_by_line():
    return jsonify(repos().reports.sales_by_line()), 200


@bp.get("/reports/quantity-distribution")
def quantity_distribution():
    return jsonify(repos().reports.quantity_distribution()), 200


# ---------------------------------------------------------------- catalog / stock
@bp.get("/reports/price-ranges")
def price_ranges():
    return jsonify(repos().reports.computers_by_price_range()), 200


@bp.get("/reports/component-usage")
def component_usage():
    return jsonify(repos().reports.component_usage(query_int("limit", default=10, minimum=1))), 200


@bp.get("/reports/inventory-by-category")
def inventory_by_category():
    return jsonify(repos().reports.inventory_by_category()), 200
