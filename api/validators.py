"""Input validation: IDs, request bodies and query params. Raises ApiError (-> 400)."""
import re
import uuid

from flask import request


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


# ---------------------------------------------------------------- IDs
# Format: <prefix>-<1..32 alphanumeric>, e.g. cmp-001, pc-3fa2b1c9, sale-001
ID_PREFIXES = {"component": "cmp", "computer": "pc", "sale": "sale",
               "client": "cli", "seller": "sel"}


def validate_id(entity, value):
    prefix = ID_PREFIXES[entity]
    if not isinstance(value, str) or not re.fullmatch(rf"{prefix}-[A-Za-z0-9]{{1,32}}", value):
        raise ApiError(f"Invalid {entity} id '{value}'. Expected format: {prefix}-<alphanumeric>")
    return value


def new_id(entity):
    return f"{ID_PREFIXES[entity]}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------- field types
def _string(value):
    return isinstance(value, str) and value.strip() != ""


def _number(value):  # bool is a subclass of int, exclude it
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _positive_integer(value):
    return _integer(value) and value > 0


def _rate(value):
    return _number(value) and value <= 1


def _email(value):
    return _string(value) and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value) is not None


def _id_list(entity):
    def check(value):
        if not isinstance(value, list) or not value:
            return False
        for item in value:
            validate_id(entity, item)
        return True
    check.expected = f"a non-empty list of {entity} ids"
    return check


def _id_of(entity):
    def check(value):
        validate_id(entity, value)
        return True
    return check


TYPE_NAMES = {_string: "non-empty string", _number: "number >= 0", _integer: "integer >= 0",
              _positive_integer: "integer > 0", _rate: "number between 0 and 1",
              _email: "valid email"}

# schema: field -> (validator, required_on_create)
COMPONENT_SCHEMA = {
    "name_component": (_string, True),
    "description_component": (_string, True),
    "price_component": (_number, True),
    "stock_component": (_integer, True),
}
COMPUTER_SCHEMA = {
    "id_component": (_id_list("component"), True),
    "name_computer": (_string, True),
    "description_computer": (_string, True),
    "price_computer": (_number, False),  # if missing: sum of its components
    "stock_computer": (_integer, True),
}
CLIENT_SCHEMA = {
    "id_client": (_id_of("client"), True),
    "full_name_client": (_string, True),
    "address": (_string, True),
    "tel_contact": (_integer, True),
    "email": (_email, True),
}
SELLER_SCHEMA = {
    "id_seller": (_id_of("seller"), True),
    "full_name_seller": (_string, True),
    "commission": (_rate, True),
}
SALE_SCHEMA = {
    "id_computer": (_id_of("computer"), True),
    "quantity": (_positive_integer, False),  # default 1
    "Client": (None, True),   # validated as embedded documents
    "Seller": (None, True),
}


def validate_body(data, schema, partial=False, context=""):
    """Returns only the schema fields, validated.
    partial=False (POST/PUT): every required field must be present.
    partial=True (PATCH): only the sent fields are validated, at least one."""
    if not isinstance(data, dict):
        raise ApiError(f"{context or 'Body'} must be a JSON object")

    unknown = [f for f in data if f not in schema and not f.startswith("id_")]
    if unknown:
        raise ApiError(f"Unknown fields{' in ' + context if context else ''}: {unknown}")

    if not partial:
        missing = [f for f, (_, required) in schema.items() if required and f not in data]
        if missing:
            raise ApiError(f"Missing fields{' in ' + context if context else ''}: {missing}")

    clean = {}
    for field, (check, _) in schema.items():
        if field not in data:
            continue
        value = data[field]
        if check is not None and not check(value):
            expected = TYPE_NAMES.get(check) or getattr(check, "expected", "a valid value")
            raise ApiError(f"Field '{field}' must be {expected}")
        clean[field] = value

    if partial and not clean:
        raise ApiError("Nothing to update")
    return clean


def validate_embedded(value, schema, name):
    """Client / Seller: accepts an object or a non-empty list of objects."""
    items = value if isinstance(value, list) else [value]
    if not items:
        raise ApiError(f"{name} cannot be empty")
    return [validate_body(item, schema, context=name) for item in items]


# ---------------------------------------------------------------- request helpers
def get_json_body():
    data = request.get_json(silent=True)
    if data is None:
        raise ApiError("Request body must be valid JSON (Content-Type: application/json)")
    return data


def query_float(name):
    raw = request.args.get(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        raise ApiError(f"Query param '{name}' must be a number")


def query_int(name, default, minimum=0):
    raw = request.args.get(name)
    if raw is None:
        return default
    if not raw.isdigit() or int(raw) < minimum:
        raise ApiError(f"Query param '{name}' must be an integer >= {minimum}")
    return int(raw)


def query_bool(name):
    raw = request.args.get(name)
    if raw is None:
        return False
    if raw.lower() not in ("true", "false"):
        raise ApiError(f"Query param '{name}' must be true or false")
    return raw.lower() == "true"
