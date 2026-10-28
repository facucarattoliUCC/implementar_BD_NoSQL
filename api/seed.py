"""Loads sample data into MongoDB. Run: python seed.py

The first documents of each collection are hand-written (tests rely on them);
the rest are generated with a fixed random seed, so every run produces the same data.
Totals: 60 components + 40 computers + 250 sales = 350 documents.
"""
import copy
import random
import unicodedata
from datetime import datetime, timedelta, timezone

TOTAL_COMPONENTS = 60
TOTAL_COMPUTERS = 40
TOTAL_SALES = 250

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


# ---------------------------------------------------------------- generated data
rng = random.Random(42)

# (category, socket, name, description, price). socket is only used to build
# compatible computers, it's not stored.
CATALOG = [
    ("cpu", "AM5", "AMD Ryzen 5 7600X", "CPU 6 cores AM5", 240.0),
    ("cpu", "AM5", "AMD Ryzen 7 7700X", "CPU 8 cores AM5", 330.0),
    ("cpu", "AM5", "AMD Ryzen 7 7800X3D", "CPU 8 cores 3D V-Cache AM5", 450.0),
    ("cpu", "AM5", "AMD Ryzen 9 7900X", "CPU 12 cores AM5", 420.0),
    ("cpu", "AM5", "AMD Ryzen 9 7950X", "CPU 16 cores AM5", 580.0),
    ("cpu", "AM5", "AMD Ryzen 5 8600G", "CPU 6 cores with Radeon graphics AM5", 210.0),
    ("cpu", "LGA1700", "Intel Core i3-14100", "CPU 4 cores LGA1700", 135.0),
    ("cpu", "LGA1700", "Intel Core i5-14400F", "CPU 10 cores LGA1700", 200.0),
    ("cpu", "LGA1700", "Intel Core i5-14600K", "CPU 14 cores LGA1700", 310.0),
    ("cpu", "LGA1700", "Intel Core i9-14900K", "CPU 24 cores LGA1700", 560.0),
    ("gpu", None, "RTX 4060 Ti", "GPU 8GB GDDR6", 400.0),
    ("gpu", None, "RTX 4070", "GPU 12GB GDDR6X", 550.0),
    ("gpu", None, "RTX 4070 Ti Super", "GPU 16GB GDDR6X", 800.0),
    ("gpu", None, "RTX 4080 Super", "GPU 16GB GDDR6X", 1000.0),
    ("gpu", None, "RTX 4090", "GPU 24GB GDDR6X", 1800.0),
    ("gpu", None, "Radeon RX 7600", "GPU 8GB GDDR6", 270.0),
    ("gpu", None, "Radeon RX 7700 XT", "GPU 12GB GDDR6", 420.0),
    ("gpu", None, "Radeon RX 7800 XT", "GPU 16GB GDDR6", 500.0),
    ("gpu", None, "Radeon RX 7900 XT", "GPU 20GB GDDR6", 720.0),
    ("gpu", None, "Intel Arc A770", "GPU 16GB GDDR6", 300.0),
    ("ram", None, "Kingston Fury Beast 16GB", "RAM DDR5 5200MHz", 60.0),
    ("ram", None, "Kingston Fury Beast 32GB", "RAM DDR5 5600MHz (2x16GB)", 110.0),
    ("ram", None, "G.Skill Trident Z5 16GB", "RAM DDR5 6000MHz", 75.0),
    ("ram", None, "G.Skill Trident Z5 32GB", "RAM DDR5 6000MHz (2x16GB)", 135.0),
    ("ram", None, "TeamGroup T-Force Delta 16GB", "RAM DDR5 RGB 5600MHz", 70.0),
    ("ram", None, "TeamGroup T-Force Delta 32GB", "RAM DDR5 RGB 6000MHz (2x16GB)", 125.0),
    ("ram", None, "Corsair Vengeance 32GB", "RAM DDR5 5600MHz (2x16GB)", 115.0),
    ("ram", None, "Corsair Vengeance 64GB", "RAM DDR5 5600MHz (2x32GB)", 210.0),
    ("ssd", None, "Samsung 990 Pro 1TB", "SSD NVMe PCIe 4.0", 110.0),
    ("ssd", None, "Samsung 990 Pro 2TB", "SSD NVMe PCIe 4.0", 180.0),
    ("ssd", None, "WD Black SN850X 1TB", "SSD NVMe PCIe 4.0", 100.0),
    ("ssd", None, "WD Black SN850X 2TB", "SSD NVMe PCIe 4.0", 170.0),
    ("ssd", None, "Crucial P3 500GB", "SSD NVMe PCIe 3.0", 40.0),
    ("ssd", None, "Crucial P3 1TB", "SSD NVMe PCIe 3.0", 60.0),
    ("ssd", None, "Kingston NV2 2TB", "SSD NVMe PCIe 4.0", 120.0),
    ("motherboard", "AM5", "ASUS TUF Gaming B650-Plus", "Motherboard AM5 ATX", 200.0),
    ("motherboard", "AM5", "MSI MAG B650 Tomahawk", "Motherboard AM5 ATX", 215.0),
    ("motherboard", "AM5", "ASRock B650M Pro RS", "Motherboard AM5 mATX", 140.0),
    ("motherboard", "AM5", "ASUS ROG Strix X670E-E", "Motherboard AM5 ATX", 450.0),
    ("motherboard", "LGA1700", "Gigabyte B760M DS3H", "Motherboard LGA1700 mATX", 115.0),
    ("motherboard", "LGA1700", "MSI B760 Gaming Plus", "Motherboard LGA1700 ATX", 150.0),
    ("motherboard", "LGA1700", "ASUS Prime H610M-E", "Motherboard LGA1700 mATX", 90.0),
    ("psu", None, "Corsair RM750e", "PSU 750W 80+ Gold", 100.0),
    ("psu", None, "Corsair RM850x", "PSU 850W 80+ Gold", 140.0),
    ("psu", None, "EVGA 600 BR", "PSU 600W 80+ Bronze", 55.0),
    ("psu", None, "Seasonic Focus GX-650", "PSU 650W 80+ Gold", 95.0),
    ("psu", None, "be quiet! Straight Power 12 1000W", "PSU 1000W 80+ Platinum", 230.0),
    ("case", None, "NZXT H5 Flow", "Case ATX mid tower", 95.0),
    ("case", None, "Lian Li Lancool 216", "Case ATX mid tower", 105.0),
    ("case", None, "Corsair 4000D Airflow", "Case ATX mid tower", 100.0),
    ("case", None, "Cooler Master Q300L", "Case mATX mini tower", 45.0),
    ("case", None, "Fractal Design North", "Case ATX mid tower, wood front", 140.0),
]

# category and socket of the hand-written components
PARTS = {"cmp-001": ("cpu", "AM5"), "cmp-002": ("cpu", "LGA1700"), "cmp-003": ("gpu", None),
         "cmp-004": ("gpu", None), "cmp-005": ("ram", None), "cmp-006": ("ssd", None),
         "cmp-007": ("motherboard", "AM5"), "cmp-008": ("motherboard", "LGA1700")}

for n, (category, socket, name, description, price) in enumerate(CATALOG, start=len(components) + 1):
    id_component = f"cmp-{n:03d}"
    PARTS[id_component] = (category, socket)
    components.append({"id_component": id_component, "name_component": name,
                       "description_component": description, "price_component": price,
                       "stock_component": rng.choice([0, 2, 3, 5, 8, 10, 12, 15, 20, 25, 30])})

assert len(components) == TOTAL_COMPONENTS
COMPONENTS_BY_ID = {c["id_component"]: c for c in components}


def _pick(category, socket=None):
    options = [i for i, (cat, sock) in PARTS.items()
               if cat == category and (socket is None or sock == socket)]
    return rng.choice(options)


LINES = [("Gamer", True), ("Creator", True), ("Streamer", True), ("Office", False), ("Home", False)]

for n in range(len(computers) + 1, TOTAL_COMPUTERS + 1):
    line, has_gpu = rng.choice(LINES)
    socket = rng.choice(["AM5", "LGA1700"])
    parts = [_pick("cpu", socket), _pick("motherboard", socket), _pick("ram"), _pick("ssd"),
             _pick("psu"), _pick("case")]
    if has_gpu:
        parts.insert(1, _pick("gpu"))
    cpu = COMPONENTS_BY_ID[parts[0]]["name_component"]
    description = (f"{cpu} + {COMPONENTS_BY_ID[parts[1]]['name_component']}" if has_gpu
                   else f"{cpu} for everyday work")
    computers.append({
        "id_computer": f"pc-{n:03d}",
        "id_component": parts,
        "name_computer": f"TechCore {line} {n:03d}",
        "description_computer": description,
        "price_computer": round(sum(COMPONENTS_BY_ID[p]["price_component"] for p in parts), 2),
        "stock_computer": rng.choice([0, 1, 2, 4, 5, 6, 8, 10, 15]),
    })

assert len(computers) == TOTAL_COMPUTERS


def _ascii(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


FIRST_NAMES = ["Lucía", "Mateo", "Valentina", "Santiago", "Camila", "Benjamín", "Martina",
               "Joaquín", "Florencia", "Tomás", "Agustina", "Nicolás", "Julieta", "Facundo"]
LAST_NAMES = ["González", "Rodríguez", "Fernández", "López", "Martínez", "Sánchez", "Romero",
              "Sosa", "Álvarez", "Torres", "Ruiz", "Ramírez", "Flores", "Acosta", "Medina"]
STREETS = ["Av. Colón", "Bv. San Juan", "Av. Vélez Sarsfield", "Av. Rafael Núñez", "Obispo Trejo",
           "Av. Hipólito Yrigoyen", "Duarte Quirós", "Av. Maipú", "La Rioja", "Av. Sabattini"]

clients = [client_1, client_2]
used_emails = {client_1["email"], client_2["email"]}
while len(clients) < 40:
    first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    email = f"{_ascii(first)}.{_ascii(last)}@mail.com"
    if email in used_emails:
        continue
    used_emails.add(email)
    clients.append({"id_client": f"cli-{len(clients) + 1:03d}",
                    "full_name_client": f"{first} {last}",
                    "address": f"{rng.choice(STREETS)} {rng.randint(100, 3500)}, Córdoba",
                    "tel_contact": int(f"351{rng.randint(4000000, 9999999)}"),
                    "email": email})

sellers = [seller_1, seller_2,
           {"id_seller": "sel-003", "full_name_seller": "Carla Moreno", "commission": 0.06},
           {"id_seller": "sel-004", "full_name_seller": "Lucas Herrera", "commission": 0.04},
           {"id_seller": "sel-005", "full_name_seller": "Paula Castro", "commission": 0.08},
           {"id_seller": "sel-006", "full_name_seller": "Ramiro Ortiz", "commission": 0.05}]

START_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)
SALES_PERIOD_MINUTES = int((datetime(2026, 10, 19, tzinfo=timezone.utc) - START_DATE).total_seconds() // 60)

for n in range(len(sales) + 1, TOTAL_SALES + 1):
    computer = rng.choice(computers)
    quantity = rng.choices([1, 2, 3], weights=[75, 20, 5])[0]
    date = START_DATE + timedelta(minutes=rng.randint(0, SALES_PERIOD_MINUTES))
    sales.append({
        "id_sale": f"sale-{n:03d}",
        "id_computer": computer["id_computer"],
        "quantity": quantity,
        "amount": round(computer["price_computer"] * quantity, 2),
        "date": date.isoformat(),
        "Client": [rng.choice(clients)],
        "Seller": [rng.choice(sellers)],
    })

assert len(sales) == TOTAL_SALES


def load(db, verbose=False):
    """Wipes the 3 collections and loads the sample data."""
    for name, docs in [("components", components), ("computers", computers), ("sales", sales)]:
        db[name].delete_many({})
        db[name].insert_many(copy.deepcopy(docs))
        if verbose:
            print(f"{name}: {len(docs)} documents")
    db.components.create_index("id_component", unique=True)
    db.computers.create_index("id_computer", unique=True)
    db.sales.create_index("id_sale", unique=True)
    if verbose:
        print(f"total: {len(components) + len(computers) + len(sales)} documents")


if __name__ == "__main__":
    from app import get_db
    load(get_db(), verbose=True)
    print("Done.")
