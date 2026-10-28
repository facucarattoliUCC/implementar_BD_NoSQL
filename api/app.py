"""
TechCore API - Flask + MongoDB
Collections: components, computers, sales (client and seller embedded in each sale).
"""
import os
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from pymongo import MongoClient, ReturnDocument

app = Flask(__name__)
app.json.sort_keys = False

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "techcore")

db = MongoClient(MONGO_URI)[DB_NAME]
components = db["components"]
computers = db["computers"]
sales = db["sales"]

NO_ID = {"_id": 0}  # hide Mongo's internal _id in every response


# ---------------------------------------------------------------- helpers
def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def error(message, status=400):
    return jsonify({"error": message}), status


def missing_fields(data, required):
    return [f for f in required if f not in data or data[f] in (None, "")]


def price_filter(prefix):
    """Builds a Mongo filter from ?min_price, ?max_price and ?in_stock."""
    query = {}
    price_key, stock_key = f"price_{prefix}", f"stock_{prefix}"
    min_p, max_p = request.args.get("min_price"), request.args.get("max_price")
    if min_p or max_p:
        query[price_key] = {}
        if min_p:
            query[price_key]["$gte"] = float(min_p)
        if max_p:
            query[price_key]["$lte"] = float(max_p)
    if request.args.get("in_stock") == "true":
        query[stock_key] = {"$gt": 0}
    if name := request.args.get("name"):
        query[f"name_{prefix}"] = {"$regex": name, "$options": "i"}
    return query


# ---------------------------------------------------------------- components
COMPONENT_REQUIRED = ["name_component", "description_component",
                      "price_component", "stock_component"]


@app.get("/components")
def list_components():
    return jsonify(list(components.find(price_filter("component"), NO_ID)))


@app.get("/components/<id_component>")
def get_component(id_component):
    doc = components.find_one({"id_component": id_component}, NO_ID)
    return jsonify(doc) if doc else error("Component not found", 404)


@app.post("/components")
def create_component():
    data = request.get_json(silent=True) or {}
    if missing := missing_fields(data, COMPONENT_REQUIRED):
        return error(f"Missing fields: {missing}")
    doc = {"id_component": data.get("id_component") or new_id("cmp"),
           **{f: data[f] for f in COMPONENT_REQUIRED}}
    if components.find_one({"id_component": doc["id_component"]}):
        return error("id_component already exists", 409)
    components.insert_one(doc.copy())
    return jsonify(doc), 201


@app.put("/components/<id_component>")
def update_component(id_component):
    data = request.get_json(silent=True) or {}
    changes = {f: data[f] for f in COMPONENT_REQUIRED if f in data}
    if not changes:
        return error("Nothing to update")
    doc = components.find_one_and_update({"id_component": id_component}, {"$set": changes},
                                         projection=NO_ID, return_document=ReturnDocument.AFTER)
    return jsonify(doc) if doc else error("Component not found", 404)


@app.delete("/components/<id_component>")
def delete_component(id_component):
    used_by = computers.count_documents({"id_component": id_component})
    if used_by:
        return error(f"Component is used by {used_by} computer(s)", 409)
    result = components.delete_one({"id_component": id_component})
    return ("", 204) if result.deleted_count else error("Component not found", 404)


# ---------------------------------------------------------------- computers
COMPUTER_REQUIRED = ["name_computer", "description_computer", "stock_computer", "id_component"]


def computer_with_components(match):
    """Computer + its referenced components resolved with $lookup."""
    pipeline = [
        {"$match": match},
        {"$lookup": {"from": "components", "localField": "id_component",
                     "foreignField": "id_component", "as": "components"}},
        {"$project": {"_id": 0, "components._id": 0}},
    ]
    return list(computers.aggregate(pipeline))


def validate_component_ids(ids):
    if not isinstance(ids, list) or not ids:
        return None, "id_component must be a non-empty list"
    found = list(components.find({"id_component": {"$in": ids}}, NO_ID))
    found_ids = {c["id_component"] for c in found}
    if unknown := [i for i in ids if i not in found_ids]:
        return None, f"Unknown components: {unknown}"
    return found, None


@app.get("/computers")
def list_computers():
    query = price_filter("computer")
    if request.args.get("expand") == "true":
        return jsonify(computer_with_components(query))
    return jsonify(list(computers.find(query, NO_ID)))


@app.get("/computers/<id_computer>")
def get_computer(id_computer):
    result = computer_with_components({"id_computer": id_computer})
    return jsonify(result[0]) if result else error("Computer not found", 404)


@app.post("/computers")
def create_computer():
    data = request.get_json(silent=True) or {}
    if missing := missing_fields(data, COMPUTER_REQUIRED):
        return error(f"Missing fields: {missing}")
    found, err = validate_component_ids(data["id_component"])
    if err:
        return error(err)
    # If no price is given, it's the sum of its components
    price = data.get("price_computer") or round(sum(c["price_component"] for c in found), 2)
    doc = {"id_computer": data.get("id_computer") or new_id("pc"),
           "id_component": data["id_component"],
           "name_computer": data["name_computer"],
           "description_computer": data["description_computer"],
           "price_computer": price,
           "stock_computer": data["stock_computer"]}
    if computers.find_one({"id_computer": doc["id_computer"]}):
        return error("id_computer already exists", 409)
    computers.insert_one(doc.copy())
    return jsonify(doc), 201


@app.put("/computers/<id_computer>")
def update_computer(id_computer):
    data = request.get_json(silent=True) or {}
    allowed = COMPUTER_REQUIRED + ["price_computer"]
    changes = {f: data[f] for f in allowed if f in data}
    if not changes:
        return error("Nothing to update")
    if "id_component" in changes:
        _, err = validate_component_ids(changes["id_component"])
        if err:
            return error(err)
    doc = computers.find_one_and_update({"id_computer": id_computer}, {"$set": changes},
                                        projection=NO_ID, return_document=ReturnDocument.AFTER)
    return jsonify(doc) if doc else error("Computer not found", 404)


@app.delete("/computers/<id_computer>")
def delete_computer(id_computer):
    result = computers.delete_one({"id_computer": id_computer})
    return ("", 204) if result.deleted_count else error("Computer not found", 404)


@app.post("/computers/build")
def build_computer():
    """Custom build: the client picks components and gets a quote + availability.
    Body: {"id_component": [...]} . Nothing is saved."""
    data = request.get_json(silent=True) or {}
    found, err = validate_component_ids(data.get("id_component"))
    if err:
        return error(err)
    out_of_stock = [c["id_component"] for c in found if c["stock_component"] <= 0]
    return jsonify({
        "components": found,
        "total_price": round(sum(c["price_component"] for c in found), 2),
        "available": not out_of_stock,
        "out_of_stock": out_of_stock,
    })


# ---------------------------------------------------------------- sales
CLIENT_REQUIRED = ["id_client", "full_name_client", "address", "tel_contact", "email"]
SELLER_REQUIRED = ["id_seller", "full_name_seller", "commission"]


@app.get("/sales")
def list_sales():
    query = {}
    if client := request.args.get("client"):
        query["Client.id_client"] = client
    if seller := request.args.get("seller"):
        query["Seller.id_seller"] = seller
    if computer := request.args.get("computer"):
        query["id_computer"] = computer
    return jsonify(list(sales.find(query, NO_ID)))


@app.get("/sales/<id_sale>")
def get_sale(id_sale):
    doc = sales.find_one({"id_sale": id_sale}, NO_ID)
    return jsonify(doc) if doc else error("Sale not found", 404)


@app.post("/sales")
def create_sale():
    """Body: {"id_computer", "quantity" (default 1), "Client": {...}, "Seller": {...}}
    Decreases the computer stock and computes the amount."""
    data = request.get_json(silent=True) or {}
    if missing := missing_fields(data, ["id_computer", "Client", "Seller"]):
        return error(f"Missing fields: {missing}")

    # Client/Seller are embedded; accept an object or a list of objects
    clients = data["Client"] if isinstance(data["Client"], list) else [data["Client"]]
    sellers = data["Seller"] if isinstance(data["Seller"], list) else [data["Seller"]]
    for c in clients:
        if missing := missing_fields(c, CLIENT_REQUIRED):
            return error(f"Client missing fields: {missing}")
    for s in sellers:
        if missing := missing_fields(s, SELLER_REQUIRED):
            return error(f"Seller missing fields: {missing}")

    quantity = int(data.get("quantity", 1))
    if quantity <= 0:
        return error("quantity must be greater than 0")

    # Atomic: only decrements if there is enough stock
    computer = computers.find_one_and_update(
        {"id_computer": data["id_computer"], "stock_computer": {"$gte": quantity}},
        {"$inc": {"stock_computer": -quantity}},
        projection=NO_ID, return_document=ReturnDocument.AFTER)
    if not computer:
        if computers.find_one({"id_computer": data["id_computer"]}):
            return error("Not enough stock", 409)
        return error("Computer not found", 404)

    doc = {"id_sale": new_id("sale"),
           "id_computer": data["id_computer"],
           "quantity": quantity,
           "amount": round(computer["price_computer"] * quantity, 2),
           "date": datetime.now(timezone.utc).isoformat(),
           "Client": [{f: c[f] for f in CLIENT_REQUIRED} for c in clients],
           "Seller": [{f: s[f] for f in SELLER_REQUIRED} for s in sellers]}
    sales.insert_one(doc.copy())
    return jsonify(doc), 201


@app.delete("/sales/<id_sale>")
def cancel_sale(id_sale):
    """Cancels a sale and returns the units to stock."""
    sale = sales.find_one_and_delete({"id_sale": id_sale})
    if not sale:
        return error("Sale not found", 404)
    computers.update_one({"id_computer": sale["id_computer"]},
                         {"$inc": {"stock_computer": sale.get("quantity", 1)}})
    return "", 204


# ---------------------------------------------------------------- reports
@app.get("/stock/low")
def low_stock():
    threshold = int(request.args.get("threshold", 5))
    return jsonify({
        "threshold": threshold,
        "components": list(components.find({"stock_component": {"$lte": threshold}}, NO_ID)),
        "computers": list(computers.find({"stock_computer": {"$lte": threshold}}, NO_ID)),
    })


@app.get("/reports/sellers")
def sales_by_seller():
    """Total sold and commission earned per seller."""
    pipeline = [
        {"$unwind": "$Seller"},
        {"$group": {"_id": "$Seller.id_seller",
                    "full_name_seller": {"$first": "$Seller.full_name_seller"},
                    "commission_rate": {"$first": "$Seller.commission"},
                    "sales_count": {"$sum": 1},
                    "total_amount": {"$sum": "$amount"}}},
        {"$project": {"_id": 0, "id_seller": "$_id", "full_name_seller": 1, "commission_rate": 1,
                      "sales_count": 1, "total_amount": 1,
                      "commission_earned": {"$multiply": ["$total_amount", "$commission_rate"]}}},
        {"$sort": {"total_amount": -1}},
    ]
    return jsonify(list(sales.aggregate(pipeline)))


@app.get("/reports/top-computers")
def top_computers():
    """Best-selling computers by units."""
    pipeline = [
        {"$group": {"_id": "$id_computer", "units_sold": {"$sum": "$quantity"},
                    "total_amount": {"$sum": "$amount"}}},
        {"$sort": {"units_sold": -1}},
        {"$limit": int(request.args.get("limit", 5))},
        {"$lookup": {"from": "computers", "localField": "_id",
                     "foreignField": "id_computer", "as": "computer"}},
        {"$project": {"_id": 0, "id_computer": "$_id", "units_sold": 1, "total_amount": 1,
                      "name_computer": {"$arrayElemAt": ["$computer.name_computer", 0]}}},
    ]
    return jsonify(list(sales.aggregate(pipeline)))


@app.errorhandler(ValueError)
def bad_value(e):
    return error(f"Invalid value: {e}")


if __name__ == "__main__":
    # Indexes on the business ids (unique)
    components.create_index("id_component", unique=True)
    computers.create_index("id_computer", unique=True)
    sales.create_index("id_sale", unique=True)
    app.run(debug=True, port=5000)
