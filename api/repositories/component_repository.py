from .base_repository import BaseRepository, NO_ID


class ComponentRepository(BaseRepository):
    collection_name = "components"
    id_field = "id_component"

    def search(self, name=None, min_price=None, max_price=None, in_stock=False):
        query = {}
        if name:
            query["name_component"] = {"$regex": name, "$options": "i"}
        if min_price is not None or max_price is not None:
            query["price_component"] = {}
            if min_price is not None:
                query["price_component"]["$gte"] = min_price
            if max_price is not None:
                query["price_component"]["$lte"] = max_price
        if in_stock:
            query["stock_component"] = {"$gt": 0}
        return self.find_all(query)

    def find_many_by_ids(self, ids):
        return list(self.collection.find({"id_component": {"$in": ids}}, NO_ID))

    def low_stock(self, threshold):
        return self.find_all({"stock_component": {"$lte": threshold}})
