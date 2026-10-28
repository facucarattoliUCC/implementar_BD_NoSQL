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
@pytest.mark.parametrize("url,n", [("/components", 8), ("/computers", 3), ("/sales", 3)])
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
def test_reports(client):
    assert client.get("/stock/low?threshold=2").status_code == 200
    assert len(client.get("/reports/sellers").get_json()) == 2
    assert client.get("/reports/top-computers?limit=2").status_code == 200
    r = client.post("/computers/build", json={"id_component": ["cmp-001", "cmp-008"]})
    assert r.get_json()["available"] is False
