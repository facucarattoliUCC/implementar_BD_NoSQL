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
