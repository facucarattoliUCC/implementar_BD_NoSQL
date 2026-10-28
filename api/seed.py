"""Loads sample data into MongoDB. Run: python seed.py"""
import os

from pymongo import MongoClient 

db = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))[os.getenv("DB_NAME", "techcore")]

components = [
    {"id_component": "cmp-001", "name_component": "AMD Ryzen 5 7600", "description_component": "CPU 6 cores AM5", "price_component": 220.0, "stock_component": 15},
    {"id_component": "cmp-002", "name_component": "Intel Core i7-14700K", "description_component": "CPU 20 cores LGA1700", "price_component": 410.0, "stock_component": 8},
    {"id_component": "cmp-003", "name_component": "RTX 4060", "description_component": "GPU 8GB GDDR6", "price_component": 310.0, "stock_component": 10},
    {"id_component": "cmp-004", "name_component": "RTX 4070 Super", "description_component": "GPU 12GB GDDR6X", "price_component": 620.0, "stock_component": 4},
    {"id_component": "cmp-005", "name_component": "Corsair Vengeance 16GB", "description_component": "RAM DDR5 5600MHz", "price_component": 65.0, "stock_component": 30},
    {"id_component": "cmp-006", "name_component": "Kingston NV2 1TB", "description_component": "SSD NVMe PCIe 4.0", "price_component": 70.0, "stock_component": 25},
    {"id_component": "cmp-007", "name_component": "Gigabyte B650M", "description_component": "Motherboard AM5 mATX", "price_component": 150.0, "stock_component": 12},
    {"id_component": "cmp-008", "name_component": "MSI Z790 Tomahawk", "description_component": "Motherboard LGA1700 ATX", "price_component": 260.0, "stock_component": 0},
]

computers = [
    {"id_computer": "pc-001", "id_component": ["cmp-001", "cmp-003", "cmp-005", "cmp-006", "cmp-007"],
     "name_computer": "TechCore Gamer Start", "description_computer": "Ryzen 5 + RTX 4060 for 1080p gaming",
     "price_computer": 835.0, "stock_computer": 6},
    {"id_computer": "pc-002", "id_component": ["cmp-002", "cmp-004", "cmp-005", "cmp-006", "cmp-008"],
     "name_computer": "TechCore Gamer Pro", "description_computer": "i7 + RTX 4070 Super for 1440p gaming",
     "price_computer": 1425.0, "stock_computer": 2},
    {"id_computer": "pc-003", "id_component": ["cmp-001", "cmp-005", "cmp-006", "cmp-007"],
     "name_computer": "TechCore Office", "description_computer": "Ryzen 5 with integrated graphics for office work",
     "price_computer": 505.0, "stock_computer": 10},
]

client_1 = {"id_client": "cli-001", "full_name_client": "Laura Gómez", "address": "Av. Colón 1234, Córdoba",
            "tel_contact": 3514567890, "email": "laura@mail.com"}
client_2 = {"id_client": "cli-002", "full_name_client": "Martín Pérez", "address": "Bv. San Juan 500, Córdoba",
            "tel_contact": 3519876543, "email": "martin@mail.com"}
seller_1 = {"id_seller": "sel-001", "full_name_seller": "Ana Torres", "commission": 0.05}
seller_2 = {"id_seller": "sel-002", "full_name_seller": "Diego Ruiz", "commission": 0.07}

sales = [
    {"id_sale": "sale-001", "id_computer": "pc-001", "quantity": 1, "amount": 835.0,
     "date": "2026-10-20T15:00:00+00:00", "Client": [client_1], "Seller": [seller_1]},
    {"id_sale": "sale-002", "id_computer": "pc-003", "quantity": 2, "amount": 1010.0,
     "date": "2026-10-22T18:30:00+00:00", "Client": [client_2], "Seller": [seller_2]},
    {"id_sale": "sale-003", "id_computer": "pc-002", "quantity": 1, "amount": 1425.0,
     "date": "2026-10-25T12:10:00+00:00", "Client": [client_1], "Seller": [seller_2]},
]

for name, docs in [("components", components), ("computers", computers), ("sales", sales)]:
    db[name].delete_many({})
    db[name].insert_many(docs)
    print(f"{name}: {len(docs)} documents")

db.components.create_index("id_component", unique=True)
db.computers.create_index("id_computer", unique=True)
db.sales.create_index("id_sale", unique=True)
print("Done.")
