from .base_repository import BaseRepository


class SaleRepository(BaseRepository):
    collection_name = "sales"
    id_field = "id_sale"

    def search(self, id_client=None, id_seller=None, id_computer=None):
        query = {}
        if id_client:
            query["Client.id_client"] = id_client
        if id_seller:
            query["Seller.id_seller"] = id_seller
        if id_computer:
            query["id_computer"] = id_computer
        return self.find_all(query)

    def count_by_computer(self, id_computer):
        return self.collection.count_documents({"id_computer": id_computer})

    def report_by_seller(self):
        pipeline = [
            {"$unwind": "$Seller"},
            {"$group": {"_id": "$Seller.id_seller",
                        "full_name_seller": {"$first": "$Seller.full_name_seller"},
                        "commission_rate": {"$first": "$Seller.commission"},
                        "sales_count": {"$sum": 1},
                        "total_amount": {"$sum": "$amount"}}},
            {"$project": {"_id": 0, "id_seller": "$_id", "full_name_seller": 1,
                          "commission_rate": 1, "sales_count": 1, "total_amount": 1,
                          "commission_earned": {"$multiply": ["$total_amount", "$commission_rate"]}}},
            {"$sort": {"total_amount": -1}},
        ]
        return list(self.collection.aggregate(pipeline))

    def top_computers(self, limit):
        pipeline = [
            {"$group": {"_id": "$id_computer", "units_sold": {"$sum": "$quantity"},
                        "total_amount": {"$sum": "$amount"}}},
            {"$sort": {"units_sold": -1}},
            {"$limit": limit},
            {"$lookup": {"from": "computers", "localField": "_id",
                         "foreignField": "id_computer", "as": "computer"}},
            {"$project": {"_id": 0, "id_computer": "$_id", "units_sold": 1, "total_amount": 1,
                          "name_computer": {"$arrayElemAt": ["$computer.name_computer", 0]}}},
        ]
        return list(self.collection.aggregate(pipeline))
