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


@bp.get("/reports/sellers")
def sales_by_seller():
    return jsonify(repos().sales.report_by_seller()), 200


@bp.get("/reports/top-computers")
def top_computers():
    return jsonify(repos().sales.top_computers(query_int("limit", default=5, minimum=1))), 200
