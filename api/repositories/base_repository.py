"""Generic repository: the only layer that talks to MongoDB."""
from pymongo import ReturnDocument

NO_ID = {"_id": 0}  # hide Mongo's internal _id in every result


class BaseRepository:
    collection_name: str = ""
    id_field: str = ""

    def __init__(self, db):
        self.collection = db[self.collection_name]

    # ---- read
    def find_all(self, query=None):
        return list(self.collection.find(query or {}, NO_ID))

    def find_by_id(self, id_):
        return self.collection.find_one({self.id_field: id_}, NO_ID)

    def exists(self, id_):
        return self.collection.count_documents({self.id_field: id_}, limit=1) > 0

    # ---- write
    def insert(self, doc):
        self.collection.insert_one(dict(doc))  # copy: insert_one adds _id
        return doc

    def replace(self, id_, doc):
        """PUT: replaces the whole document. Returns None if it doesn't exist."""
        return self.collection.find_one_and_replace(
            {self.id_field: id_}, doc,
            projection=NO_ID, return_document=ReturnDocument.AFTER)

    def update(self, id_, changes):
        """PATCH: updates only the given fields. Returns None if it doesn't exist."""
        return self.collection.find_one_and_update(
            {self.id_field: id_}, {"$set": changes},
            projection=NO_ID, return_document=ReturnDocument.AFTER)

    def delete(self, id_):
        return self.collection.delete_one({self.id_field: id_}).deleted_count > 0

    def ensure_indexes(self):
        self.collection.create_index(self.id_field, unique=True)
