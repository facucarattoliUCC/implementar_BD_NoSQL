"""Landing page at "/": API status and the list of endpoints.
The endpoint list is built from Flask's url_map, so new routes show up automatically."""
from flask import Blueprint, current_app, render_template

from . import repos

bp = Blueprint("home", __name__)

SECTIONS = {
    "components": "Components",
    "computers": "Computers",
    "sales": "Sales",
    "reports": "Stock & reports",
}

# Short description per (method, rule). Routes not listed here use their docstring.
DESCRIPTIONS = {
    ("GET", "/components"): "List components. Filters: name, min_price, max_price, in_stock",
    ("POST", "/components"): "Create a component",
    ("GET", "/components/<id_component>"): "Get a component",
    ("PUT", "/components/<id_component>"): "Replace a component (all fields)",
    ("PATCH", "/components/<id_component>"): "Update some fields of a component",
    ("DELETE", "/components/<id_component>"): "Delete a component (not if a computer uses it)",
    ("GET", "/computers"): "List computers. Filters: name, min_price, max_price, in_stock, expand",
    ("POST", "/computers"): "Create a computer from a list of components",
    ("POST", "/computers/build"): "Quote a custom build: total price and availability",
    ("GET", "/computers/<id_computer>"): "Get a computer with its components",
    ("PUT", "/computers/<id_computer>"): "Replace a computer (all fields)",
    ("PATCH", "/computers/<id_computer>"): "Update some fields of a computer",
    ("DELETE", "/computers/<id_computer>"): "Delete a computer (not if it has sales)",
    ("GET", "/sales"): "List sales. Filters: client, seller, computer",
    ("POST", "/sales"): "Register a sale (decrements stock)",
    ("GET", "/sales/<id_sale>"): "Get a sale",
    ("PUT", "/sales/<id_sale>"): "Replace a sale (stock is readjusted)",
    ("PATCH", "/sales/<id_sale>"): "Update some fields of a sale (stock is readjusted)",
    ("DELETE", "/sales/<id_sale>"): "Cancel a sale (stock is returned)",
    ("GET", "/stock/low"): "Components and computers with low stock. Param: threshold",
    ("GET", "/reports/summary"): "General KPIs",
    ("GET", "/reports/sales-by-month"): "Sales, units and revenue per month",
    ("GET", "/reports/sellers"): "Total sold and commission per seller",
    ("GET", "/reports/top-computers"): "Best-selling computers. Param: limit",
    ("GET", "/reports/top-clients"): "Clients who spent the most. Param: limit",
    ("GET", "/reports/sales-by-line"): "Revenue per product line",
    ("GET", "/reports/quantity-distribution"): "Sales grouped by units per sale",
    ("GET", "/reports/price-ranges"): "Computers per price range",
    ("GET", "/reports/component-usage"): "Components used in the most computers. Param: limit",
    ("GET", "/reports/inventory-by-category"): "Stock and inventory value per category",
}

METHOD_ORDER = ["GET", "POST", "PUT", "PATCH", "DELETE"]


def _endpoints():
    """Groups the registered routes by blueprint: {section: [{method, rule, description, link}]}"""
    groups = {name: [] for name in SECTIONS.values()}
    for rule in current_app.url_map.iter_rules():
        blueprint = rule.endpoint.split(".")[0]
        if blueprint not in SECTIONS:
            continue
        view = current_app.view_functions[rule.endpoint]
        doc = (view.__doc__ or "").strip().splitlines()
        for method in sorted(rule.methods & set(METHOD_ORDER), key=METHOD_ORDER.index):
            groups[SECTIONS[blueprint]].append({
                "method": method,
                "rule": rule.rule,
                "description": DESCRIPTIONS.get((method, rule.rule), doc[0] if doc else ""),
                # GET routes without parameters can be opened directly
                "link": rule.rule if method == "GET" and "<" not in rule.rule else None,
            })
    # Order: as listed in DESCRIPTIONS; routes not listed go last
    order = {key: i for i, key in enumerate(DESCRIPTIONS)}
    for items in groups.values():
        items.sort(key=lambda e: (order.get((e["method"], e["rule"]), len(order)), e["rule"]))
    return groups


def _status():
    """Database status and document count per collection. Never raises."""
    try:
        r = repos()
        counts = {
            "components": r.components.collection.count_documents({}),
            "computers": r.computers.collection.count_documents({}),
            "sales": r.sales.collection.count_documents({}),
        }
        return {"ok": True, "counts": counts, "database": r.components.collection.database.name}
    except Exception:  # Mongo down, timeout...
        current_app.logger.exception("Database not reachable from the home page")
        return {"ok": False, "counts": {}, "database": None}


@bp.get("/")
def index():
    return render_template("index.html", status=_status(), groups=_endpoints())
