"""Read-only aggregations that combine the 3 collections. Every method returns
plain lists/dicts ready to be turned into a DataFrame or a chart."""


def _first_word(field):
    return {"$arrayElemAt": [{"$split": [field, " "]}, 0]}


def _second_word(field):
    return {"$arrayElemAt": [{"$split": [field, " "]}, 1]}


def _round(expr):
    """Marks a field to be rounded. $round is applied in Python (see _rounded) so the
    pipelines also run on MongoDB < 4.2 and on mongomock (tests)."""
    return expr


def _rounded(rows, digits=2):
    """Rounds every float of the aggregation result."""
    return [{k: round(v, digits) if isinstance(v, float) else v for k, v in row.items()}
            for row in rows]


class ReportRepository:
    PRICE_RANGES = [0, 750, 1000, 1500, 2000, 3000]

    def __init__(self, db):
        self.components = db["components"]
        self.computers = db["computers"]
        self.sales = db["sales"]

    # ---------------------------------------------------------------- sales
    def summary(self):
        """General KPIs of the business."""
        totals = list(self.sales.aggregate([
            {"$group": {"_id": None, "sales_count": {"$sum": 1},
                        "units_sold": {"$sum": "$quantity"},
                        "total_revenue": {"$sum": "$amount"},
                        "average_ticket": {"$avg": "$amount"},
                        "first_sale": {"$min": "$date"}, "last_sale": {"$max": "$date"}}},
        ]))
        result = totals[0] if totals else {"sales_count": 0, "units_sold": 0, "total_revenue": 0,
                                            "average_ticket": 0, "first_sale": None, "last_sale": None}
        result.pop("_id", None)
        result["total_revenue"] = round(result["total_revenue"], 2)
        result["average_ticket"] = round(result["average_ticket"] or 0, 2)
        result["clients_count"] = len(self.sales.distinct("Client.id_client"))
        result["sellers_count"] = len(self.sales.distinct("Seller.id_seller"))
        result["computers_count"] = self.computers.count_documents({})
        result["components_count"] = self.components.count_documents({})
        return result

    def sales_by_month(self):
        """Sales, units and revenue per month (date is stored as ISO string: YYYY-MM-...)."""
        return _rounded(self.sales.aggregate([
            {"$group": {"_id": {"$substr": ["$date", 0, 7]},
                        "sales_count": {"$sum": 1},
                        "units_sold": {"$sum": "$quantity"},
                        "revenue": {"$sum": "$amount"}}},
            {"$sort": {"_id": 1}},
            {"$project": {"_id": 0, "month": "$_id", "sales_count": 1, "units_sold": 1,
                          "revenue": _round("$revenue")}},
        ]))

    def sales_by_seller(self):
        """Total sold and commission earned per seller."""
        return _rounded(self.sales.aggregate([
            {"$unwind": "$Seller"},
            {"$group": {"_id": "$Seller.id_seller",
                        "full_name_seller": {"$first": "$Seller.full_name_seller"},
                        "commission_rate": {"$first": "$Seller.commission"},
                        "sales_count": {"$sum": 1},
                        "total_amount": {"$sum": "$amount"}}},
            {"$project": {"_id": 0, "id_seller": "$_id", "full_name_seller": 1,
                          "commission_rate": 1, "sales_count": 1,
                          "total_amount": _round("$total_amount"),
                          "commission_earned": _round({"$multiply": ["$total_amount",
                                                                     "$commission_rate"]})}},
            {"$sort": {"total_amount": -1}},
        ]))

    def top_computers(self, limit):
        """Best-selling computers by units."""
        return _rounded(self.sales.aggregate([
            {"$group": {"_id": "$id_computer", "units_sold": {"$sum": "$quantity"},
                        "total_amount": {"$sum": "$amount"}}},
            {"$sort": {"units_sold": -1, "total_amount": -1}},
            {"$limit": limit},
            {"$lookup": {"from": "computers", "localField": "_id",
                         "foreignField": "id_computer", "as": "computer"}},
            {"$project": {"_id": 0, "id_computer": "$_id", "units_sold": 1,
                          "total_amount": _round("$total_amount"),
                          "name_computer": {"$arrayElemAt": ["$computer.name_computer", 0]}}},
        ]))

    def top_clients(self, limit):
        """Clients who spent the most."""
        return _rounded(self.sales.aggregate([
            {"$unwind": "$Client"},
            {"$group": {"_id": "$Client.id_client",
                        "full_name_client": {"$first": "$Client.full_name_client"},
                        "purchases": {"$sum": 1},
                        "units_bought": {"$sum": "$quantity"},
                        "total_spent": {"$sum": "$amount"},
                        "average_ticket": {"$avg": "$amount"}}},
            {"$sort": {"total_spent": -1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "id_client": "$_id", "full_name_client": 1, "purchases": 1,
                          "units_bought": 1, "total_spent": _round("$total_spent"),
                          "average_ticket": _round("$average_ticket")}},
        ]))

    def sales_by_line(self):
        """Revenue per product line. The line is the 2nd word of the computer name
        (TechCore <Gamer|Office|Creator|Streamer|Home> ...)."""
        return _rounded(self.sales.aggregate([
            {"$lookup": {"from": "computers", "localField": "id_computer",
                         "foreignField": "id_computer", "as": "computer"}},
            {"$unwind": "$computer"},
            {"$group": {"_id": _second_word("$computer.name_computer"),
                        "sales_count": {"$sum": 1},
                        "units_sold": {"$sum": "$quantity"},
                        "revenue": {"$sum": "$amount"}}},
            {"$sort": {"revenue": -1}},
            {"$project": {"_id": 0, "line": "$_id", "sales_count": 1, "units_sold": 1,
                          "revenue": _round("$revenue")}},
        ]))

    def quantity_distribution(self):
        """How many sales were of 1, 2, 3... units."""
        return _rounded(self.sales.aggregate([
            {"$group": {"_id": "$quantity", "sales_count": {"$sum": 1},
                        "revenue": {"$sum": "$amount"}}},
            {"$sort": {"_id": 1}},
            {"$project": {"_id": 0, "quantity": "$_id", "sales_count": 1,
                          "revenue": _round("$revenue")}},
        ]))

    # ---------------------------------------------------------------- catalog / stock
    def computers_by_price_range(self):
        """Computers grouped by price range ($bucket)."""
        bounds = self.PRICE_RANGES
        labels = {low: f"{low}-{high}" for low, high in zip(bounds, bounds[1:])}
        result = list(self.computers.aggregate([
            {"$bucket": {"groupBy": "$price_computer", "boundaries": bounds,
                         "default": f"{bounds[-1]}+",
                         "output": {"computers_count": {"$sum": 1},
                                    "stock": {"$sum": "$stock_computer"},
                                    "average_price": {"$avg": "$price_computer"}}}},
        ]))
        by_range = {r["_id"]: r for r in result}
        ranges = list(labels.items()) + [(f"{bounds[-1]}+", f"{bounds[-1]}+")]
        return [{"price_range": label,
                 "computers_count": by_range.get(key, {}).get("computers_count", 0),
                 "stock": by_range.get(key, {}).get("stock", 0),
                 "average_price": round(by_range.get(key, {}).get("average_price") or 0, 2)}
                for key, label in ranges]

    def component_usage(self, limit):
        """Components that appear in the most computers."""
        return _rounded(self.computers.aggregate([
            {"$unwind": "$id_component"},
            {"$group": {"_id": "$id_component", "used_in_computers": {"$sum": 1}}},
            {"$sort": {"used_in_computers": -1, "_id": 1}},
            {"$limit": limit},
            {"$lookup": {"from": "components", "localField": "_id",
                         "foreignField": "id_component", "as": "component"}},
            {"$unwind": "$component"},
            {"$project": {"_id": 0, "id_component": "$_id",
                          "name_component": "$component.name_component",
                          "category": _first_word("$component.description_component"),
                          "used_in_computers": 1,
                          "stock_component": "$component.stock_component"}},
        ]))

    def inventory_by_category(self):
        """Stock and inventory value (price x stock) per component category.
        The category is the 1st word of the description (CPU, GPU, RAM, SSD...)."""
        return _rounded(self.components.aggregate([
            {"$group": {"_id": _first_word("$description_component"),
                        "components_count": {"$sum": 1},
                        "out_of_stock": {"$sum": {"$cond": [{"$lte": ["$stock_component", 0]}, 1, 0]}},
                        "units_in_stock": {"$sum": "$stock_component"},
                        "inventory_value": {"$sum": {"$multiply": ["$price_component",
                                                                   "$stock_component"]}},
                        "average_price": {"$avg": "$price_component"}}},
            {"$sort": {"inventory_value": -1}},
            {"$project": {"_id": 0, "category": "$_id", "components_count": 1, "out_of_stock": 1,
                          "units_in_stock": 1, "inventory_value": _round("$inventory_value"),
                          "average_price": _round("$average_price")}},
        ]))
