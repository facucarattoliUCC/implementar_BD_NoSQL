from pymongo import ReturnDocument

from .base_repository import BaseRepository, NO_ID


class ComputerRepository(BaseRepository):
    collection_name = "computers"
    id_field = "id_computer"

    def search(self, name=None, min_price=None, max_price=None, in_stock=False, expand=False):
        query = {}
        if name:
            query["name_computer"] = {"$regex": name, "$options": "i"}
        if min_price is not None or max_price is not None:
            query["price_computer"] = {}
            if min_price is not None:
                query["price_computer"]["$gte"] = min_price
            if max_price is not None:
                query["price_computer"]["$lte"] = max_price
        if in_stock:
            query["stock_computer"] = {"$gt": 0}
        return self.find_with_components(query) if expand else self.find_all(query)

    def find_with_components(self, match):
        """Resolves the referenced components with $lookup."""
        pipeline = [
            {"$match": match},
            {"$lookup": {"from": "components", "localField": "id_component",
                         "foreignField": "id_component", "as": "components"}},
            {"$project": {"_id": 0, "components._id": 0}},
        ]
        return list(self.collection.aggregate(pipeline))

    def find_by_id_expanded(self, id_computer):
        result = self.find_with_components({"id_computer": id_computer})
        return result[0] if result else None

    def count_using_component(self, id_component):
        return self.collection.count_documents({"id_component": id_component})

    def decrement_stock(self, id_computer, quantity):
        """Atomic: only decrements if there is enough stock. Returns None otherwise."""
        return self.collection.find_one_and_update(
            {"id_computer": id_computer, "stock_computer": {"$gte": quantity}},
            {"$inc": {"stock_computer": -quantity}},
            projection=NO_ID, return_document=ReturnDocument.AFTER)

    def increment_stock(self, id_computer, quantity):
        self.collection.update_one({"id_computer": id_computer},
                                   {"$inc": {"stock_computer": quantity}})

    def low_stock(self, threshold):
        return self.find_all({"stock_computer": {"$lte": threshold}})
