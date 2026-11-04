"""Run: pytest -v   (uses mongomock, no real MongoDB needed)"""
import os
import sys

import mongomock
import pytest
from pymongo.errors import ServerSelectionTimeoutError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import seed  # noqa: E402
from app import create_app  # noqa: E402

COMPONENT = {"name_component": "RAM 32GB", "description_component": "DDR5",
             "price_component": 120.0, "stock_component": 10}
CLIENT = {"id_client": "cli-009", "full_name_client": "Sofía Díaz", "address": "Calle 1",
          "tel_contact": 3511111111, "email": "sofia@mail.com"}
SELLER = {"id_seller": "sel-001", "full_name_seller": "Ana Torres", "commission": 0.05}


@pytest.fixture
def db():
    database = mongomock.MongoClient()["techcore_test"]
    seed.load(database)
    return database


@pytest.fixture
def client(db):
    app = create_app(db)
    app.config["TESTING"] = True
    return app.test_client()


# ---------------------------------------------------------------- CRUD
@pytest.mark.parametrize("url,n", [("/components", 60), ("/computers", 40), ("/sales", 250)])
def test_list(client, url, n):
    r = client.get(url)
    assert r.status_code == 200 and len(r.get_json()) == n


def test_component_crud(client):
    r = client.post("/components", json=COMPONENT)
    assert r.status_code == 201
    id_ = r.get_json()["id_component"]

    assert client.get(f"/components/{id_}").status_code == 200

    r = client.patch(f"/components/{id_}", json={"stock_component": 3})
    assert r.status_code == 200 and r.get_json()["stock_component"] == 3
    assert r.get_json()["name_component"] == "RAM 32GB"          # PATCH keeps the rest

    r = client.put(f"/components/{id_}", json={**COMPONENT, "price_component": 99})
    assert r.status_code == 200 and r.get_json()["price_component"] == 99

    assert client.delete(f"/components/{id_}").status_code == 200
    assert client.get(f"/components/{id_}").status_code == 404


def test_computer_crud(client):
    body = {"id_component": ["cmp-001", "cmp-005"], "name_computer": "Mini",
            "description_computer": "Small", "stock_computer": 2}
    r = client.post("/computers", json=body)
    assert r.status_code == 201 and r.get_json()["price_computer"] == 285.0  # sum of components
    id_ = r.get_json()["id_computer"]

    r = client.get(f"/computers/{id_}")
    assert len(r.get_json()["components"]) == 2                 # $lookup resolved

    assert client.patch(f"/computers/{id_}", json={"stock_computer": 7}).status_code == 200
    assert client.put(f"/computers/{id_}", json={**body, "price_computer": 300}).status_code == 200
    assert client.delete(f"/computers/{id_}").status_code == 200


def test_sale_crud_and_stock(client):
    stock = lambda: client.get("/computers/pc-003").get_json()["stock_computer"]
    assert stock() == 10

    r = client.post("/sales", json={"id_computer": "pc-003", "quantity": 2,
                                    "Client": CLIENT, "Seller": SELLER})
    assert r.status_code == 201 and r.get_json()["amount"] == 1010.0
    id_ = r.get_json()["id_sale"]
    assert stock() == 8

    r = client.patch(f"/sales/{id_}", json={"quantity": 3})
    assert r.status_code == 200 and r.get_json()["amount"] == 1515.0
    assert stock() == 7

    r = client.patch(f"/sales/{id_}", json={"Client": {**CLIENT, "address": "Calle 2"}})
    assert r.get_json()["Client"][0]["address"] == "Calle 2"

    r = client.put(f"/sales/{id_}", json={"id_computer": "pc-001", "quantity": 1,
                                          "Client": CLIENT, "Seller": SELLER})
    assert r.status_code == 200 and r.get_json()["amount"] == 835.0
    assert stock() == 10                                        # units returned to pc-003

    assert client.delete(f"/sales/{id_}").status_code == 200
    assert client.get(f"/sales/{id_}").status_code == 404


# ---------------------------------------------------------------- 400: invalid IDs
@pytest.mark.parametrize("url", ["/components/abc", "/computers/cmp-001",
                                 "/sales/sale-$$", "/sales?client=xx"])
def test_invalid_id_format(client, url):
    r = client.get(url)
    assert r.status_code == 400 and "Invalid" in r.get_json()["error"]


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_invalid_id_on_write(client, method):
    assert getattr(client, method)("/components/bad id", json=COMPONENT).status_code == 400


# ---------------------------------------------------------------- 400: invalid bodies
@pytest.mark.parametrize("body", [
    {**COMPONENT, "price_component": "abc"},          # wrong type
    {**COMPONENT, "stock_component": -1},             # negative
    {k: v for k, v in COMPONENT.items() if k != "name_component"},  # missing field
    {**COMPONENT, "color": "red"},                    # unknown field
])
def test_invalid_component_body(client, body):
    assert client.post("/components", json=body).status_code == 400


def test_no_json_body(client):
    r = client.post("/components", data="not json", content_type="text/plain")
    assert r.status_code == 400


def test_empty_patch(client):
    assert client.patch("/components/cmp-001", json={}).status_code == 400


def test_computer_unknown_component(client):
    body = {"id_component": ["cmp-999"], "name_computer": "X",
            "description_computer": "Y", "stock_computer": 1}
    assert client.post("/computers", json=body).status_code == 400


def test_sale_invalid_embedded(client):
    bad_client = {**CLIENT, "email": "not-an-email"}
    r = client.post("/sales", json={"id_computer": "pc-001", "Client": bad_client, "Seller": SELLER})
    assert r.status_code == 400


def test_sale_not_enough_stock(client):
    r = client.post("/sales", json={"id_computer": "pc-002", "quantity": 50,
                                    "Client": CLIENT, "Seller": SELLER})
    assert r.status_code == 400


def test_delete_component_in_use(client):
    assert client.delete("/components/cmp-001").status_code == 400


def test_invalid_query_param(client):
    assert client.get("/components?min_price=abc").status_code == 400


# ---------------------------------------------------------------- 404
@pytest.mark.parametrize("url", ["/components/cmp-999", "/computers/pc-999",
                                 "/sales/sale-999", "/route-that-does-not-exist"])
def test_not_found(client, url):
    r = client.get(url)
    assert r.status_code == 404 and "error" in r.get_json()


def test_sale_computer_not_found(client):
    r = client.post("/sales", json={"id_computer": "pc-999", "Client": CLIENT, "Seller": SELLER})
    assert r.status_code == 404


# ---------------------------------------------------------------- 500
def test_database_error_returns_500(client, monkeypatch):
    def boom(*args, **kwargs):
        raise ServerSelectionTimeoutError("Mongo is down")
    repo = client.application.extensions["repos"].components
    monkeypatch.setattr(repo, "search", boom)
    r = client.get("/components")
    assert r.status_code == 500 and r.get_json()["error"] == "Database error"


# ---------------------------------------------------------------- extras
def test_seed_data_is_valid(client):
    """Every generated document passes the same validations as the API."""
    from validators import (CLIENT_SCHEMA, COMPONENT_SCHEMA, COMPUTER_SCHEMA, SELLER_SCHEMA,
                            validate_body, validate_id)
    ids = {c["id_component"] for c in seed.components}
    for c in seed.components:
        validate_id("component", c["id_component"])
        validate_body({k: v for k, v in c.items() if k != "id_component"}, COMPONENT_SCHEMA)
    for pc in seed.computers:
        validate_id("computer", pc["id_computer"])
        validate_body({k: v for k, v in pc.items() if k != "id_computer"}, COMPUTER_SCHEMA)
        assert set(pc["id_component"]) <= ids
    for s in seed.sales:
        validate_id("sale", s["id_sale"])
        validate_body(s["Client"][0], CLIENT_SCHEMA)
        validate_body(s["Seller"][0], SELLER_SCHEMA)
    total = len(seed.components) + len(seed.computers) + len(seed.sales)
    assert total >= 300


def test_build_quote(client):
    r = client.post("/computers/build", json={"id_component": ["cmp-001", "cmp-008"]})
    assert r.get_json()["available"] is False


# ---------------------------------------------------------------- reports
# Each report is checked against the same number computed in plain Python from seed data.
TOTAL_REVENUE = round(sum(s["amount"] for s in seed.sales), 2)


@pytest.mark.parametrize("url", [
    "/stock/low?threshold=2", "/reports/summary", "/reports/sales-by-month", "/reports/sellers",
    "/reports/top-computers?limit=3", "/reports/top-clients?limit=3", "/reports/sales-by-line",
    "/reports/quantity-distribution", "/reports/price-ranges", "/reports/component-usage?limit=3",
    "/reports/inventory-by-category"])
def test_report_ok(client, url):
    r = client.get(url)
    assert r.status_code == 200 and r.get_json()


@pytest.mark.parametrize("url", ["/reports/top-clients?limit=0", "/reports/component-usage?limit=x",
                                 "/reports/top-computers?limit=-1"])
def test_report_invalid_limit(client, url):
    assert client.get(url).status_code == 400


def test_report_summary(client):
    r = client.get("/reports/summary").get_json()
    assert r["sales_count"] == 250
    assert r["total_revenue"] == TOTAL_REVENUE
    assert r["units_sold"] == sum(s["quantity"] for s in seed.sales)
    assert r["clients_count"] == len({s["Client"][0]["id_client"] for s in seed.sales})
    assert r["sellers_count"] == 6


def test_report_sales_by_month(client):
    rows = client.get("/reports/sales-by-month").get_json()
    months = [r["month"] for r in rows]
    assert months == sorted(months) and months[0] == "2026-01"
    assert sum(r["sales_count"] for r in rows) == 250
    assert round(sum(r["revenue"] for r in rows), 2) == TOTAL_REVENUE


def test_report_sellers(client):
    rows = client.get("/reports/sellers").get_json()
    assert len(rows) == 6
    for r in rows:
        assert r["commission_earned"] == round(r["total_amount"] * r["commission_rate"], 2)


def test_report_top_clients(client):
    rows = client.get("/reports/top-clients?limit=5").get_json()
    assert len(rows) == 5
    spent = [r["total_spent"] for r in rows]
    assert spent == sorted(spent, reverse=True)


def test_report_sales_by_line(client):
    rows = client.get("/reports/sales-by-line").get_json()
    assert {r["line"] for r in rows} <= {"Gamer", "Creator", "Streamer", "Office", "Home"}
    assert round(sum(r["revenue"] for r in rows), 2) == TOTAL_REVENUE


def test_report_price_ranges(client):
    rows = client.get("/reports/price-ranges").get_json()
    assert rows[0]["price_range"] == "0-750"
    assert sum(r["computers_count"] for r in rows) == 40


def test_report_component_usage(client):
    rows = client.get("/reports/component-usage?limit=1").get_json()
    usage = {}
    for pc in seed.computers:
        for c in pc["id_component"]:
            usage[c] = usage.get(c, 0) + 1
    assert rows[0]["used_in_computers"] == max(usage.values())


def test_report_inventory_by_category(client):
    rows = client.get("/reports/inventory-by-category").get_json()
    assert {r["category"] for r in rows} == {"CPU", "GPU", "RAM", "SSD", "Motherboard", "PSU", "Case"}
    assert sum(r["components_count"] for r in rows) == 60
    expected = round(sum(c["price_component"] * c["stock_component"] for c in seed.components), 2)
    assert round(sum(r["inventory_value"] for r in rows), 2) == expected


# ---------------------------------------------------------------- home page
def test_home_page(client):
    r = client.get("/")
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and r.content_type.startswith("text/html")
    assert "Connected" in html
    assert 'href="/reports/summary"' in html          # GET without params is a link
    assert "/components/&lt;id_component&gt;" in html   # route with param is listed


def test_home_page_database_down(client, monkeypatch):
    def boom(*args, **kwargs):
        raise ServerSelectionTimeoutError("Mongo is down")
    monkeypatch.setattr(client.application.extensions["repos"].components.collection,
                        "count_documents", boom)
    r = client.get("/")
    assert r.status_code == 200 and "Not reachable" in r.get_data(as_text=True)
