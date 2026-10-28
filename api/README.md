# TechCore API (Flask + PyMongo, Repository pattern)

## Setup
```bash
pip install -r requirements.txt
# MongoDB on localhost:27017 (or set MONGO_URI / DB_NAME)
python seed.py     # loads sample data
python app.py      # http://localhost:5000
pytest -v          # 31 tests, use mongomock (no MongoDB needed)
```

## Structure
```
techcore-api/
├── app.py                  # create_app(): registers repositories, blueprints and error handlers
├── validators.py           # ID format, body schemas, query params -> ApiError (400)
├── seed.py                 # sample data
├── repositories/           # data access layer: the ONLY code that uses PyMongo
│   ├── base_repository.py  #   find_all, find_by_id, exists, insert, replace, update, delete
│   ├── component_repository.py
│   ├── computer_repository.py   # + $lookup of components, atomic stock decrement
│   └── sale_repository.py       # + aggregation reports
├── routes/                 # HTTP layer (Flask blueprints): validates and returns status codes
│   ├── components.py
│   ├── computers.py
│   ├── sales.py
│   └── reports.py
└── tests/test_api.py
```

**Flow of a request:** `route` validates the ID and body → calls the `repository` → the repository runs the PyMongo query → the route returns JSON + status code. Routes never touch a Mongo collection directly.

## Endpoints (CRUD)

Same pattern for `/components`, `/computers` and `/sales`:

| Method | Route | Description | OK |
|---|---|---|---|
| GET | `/<resource>` | List (with filters) | 200 |
| GET | `/<resource>/<id>` | Get one | 200 |
| POST | `/<resource>` | Create | 201 |
| PUT | `/<resource>/<id>` | Full replacement (all required fields) | 200 |
| PATCH | `/<resource>/<id>` | Partial update (only sent fields) | 200 |
| DELETE | `/<resource>/<id>` | Delete | 200 |

List filters:
- `/components`, `/computers`: `?name=`, `?min_price=`, `?max_price=`, `?in_stock=true`; computers also `?expand=true`
- `/sales`: `?client=cli-001`, `?seller=sel-001`, `?computer=pc-001`

Business rules:
- **Computer**: `id_component` is a list of existing components; if `price_computer` is not sent it's the sum of the components. `GET /computers/<id>` returns the components resolved.
- **Sale**: `Client` and `Seller` are embedded. Creating a sale decrements the computer stock atomically and computes `amount`; changing `id_computer`/`quantity` by PUT/PATCH moves the stock; DELETE returns it.
- A component used by a computer, or a computer with sales, cannot be deleted (400).

Extras: `POST /computers/build` (custom build quote), `GET /stock/low?threshold=5`, `GET /reports/sellers`, `GET /reports/top-computers?limit=5`.

## IDs
Format `<prefix>-<alphanumeric>` (max 32 chars). A malformed ID returns **400**, a well-formed one that doesn't exist returns **404**.

| Entity | Prefix | Example |
|---|---|---|
| Component | `cmp` | `cmp-001` |
| Computer | `pc` | `pc-001` |
| Sale | `sale` | `sale-001` |
| Client | `cli` | `cli-001` |
| Seller | `sel` | `sel-001` |

## Status codes
Every error is JSON: `{"error": "...", "status": <code>}`

| Code | When |
|---|---|
| 200 | GET, PUT, PATCH, DELETE ok |
| 201 | POST ok |
| 400 | Malformed ID, invalid JSON, missing/unknown field, wrong type, empty PATCH, nonexistent referenced component, not enough stock, duplicate id, deleting something in use, invalid query param |
| 404 | ID doesn't exist, or unknown route |
| 405 | Method not allowed on that route |
| 500 | MongoDB error (down, timeout) or any unexpected error — logged, never exposes the traceback |

## Example
```bash
curl -X POST localhost:5000/sales -H "Content-Type: application/json" -d '{
  "id_computer": "pc-001", "quantity": 1,
  "Client": {"id_client": "cli-003", "full_name_client": "Sofía Díaz", "address": "Calle 1", "tel_contact": 3511111111, "email": "sofia@mail.com"},
  "Seller": {"id_seller": "sel-001", "full_name_seller": "Ana Torres", "commission": 0.05}
}'

curl -X PATCH localhost:5000/components/cmp-003 -H "Content-Type: application/json" -d '{"stock_component": 20}'
```
